from firebase_functions import https_fn, options
from firebase_admin import initialize_app, firestore
import firebase_admin
from firebase_admin import auth as firebase_auth
import pandas as pd
import json
import requests
import numpy as np
import os
from dotenv import load_dotenv
import math
import datetime
import traceback
import functools
import io

# Hawkin Dynamics: direct HTTP client (replaces hdforce SDK)
from hawkin_client import HawkinClient

_hd_client_singleton = None
def _hd_client() -> HawkinClient:
    """Lazy-construct one client per function instance. Reuses the access token cache."""
    global _hd_client_singleton
    if _hd_client_singleton is None:
        _hd_client_singleton = HawkinClient()
    return _hd_client_singleton

# Cache for HD tests to make rapid clicking in the UI instantaneous
hd_cache = {
    "CMJ": None,
    "CMJ_REBOUND": None,
}

valor_cache = {
    "sessions": None
}

# Safely load the .env variables and strip any quotes
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

# Initialize firebase_admin eagerly (fast — needed for auth.get_user, etc.)
# but defer firestore.client() since that's the slow part that times out
# Firebase's deployment-time function discovery (10s limit).
if not firebase_admin._apps:
    cred_path = os.path.join(os.path.dirname(__file__), "..", "service-account.json")
    if os.path.exists(cred_path):
        from firebase_admin import credentials
        initialize_app(credentials.Certificate(cred_path))
    else:
        initialize_app()

class _LazyFirestore:
    _client = None
    def _ensure(self):
        if _LazyFirestore._client is None:
            _LazyFirestore._client = firestore.client()
        return _LazyFirestore._client
    def __getattr__(self, name):
        return getattr(self._ensure(), name)

db = _LazyFirestore()

def get_jwt_token():
    username = os.environ.get("VALOR_USER", "").strip().strip("\"'")
    password = os.environ.get("VALOR_PASSWORD", "").strip().strip("\"'")
    client_id = os.environ.get("VALOR_CLIENT_ID", "").strip().strip("\"'")
    token_url = os.environ.get("VALOR_TOKEN_URL", "").strip().strip("\"'")

    payload = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": client_id,
        "AuthParameters": {
            "USERNAME": username,
            "PASSWORD": password
        }
    }
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "User-Agent": "insomnia/11.3.0",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"
    }

    response = requests.post(token_url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json().get("AuthenticationResult", {})
        return data.get("IdToken")
    else:
        print(f"Valor Auth failed ({response.status_code}): {response.text}")
        return None

def extract_valor_score(data: dict) -> float:
    """Helper to extract and average the Score values from a Valor JSON response."""
    ang_data = data.get("WorkoutMetrics", {}).get("Ang", {})
    scores = []
    for metric, side_dict in ang_data.items():
        for side in side_dict:
            val = side_dict.get(side, {})
            if "Score" in val and val["Score"] is not None:
                scores.append(val["Score"])
    if scores:
        return float(np.mean(scores) * 100)
    return 0.0

def clean_payload(obj):
    """Recursively scrub data to ensure it is 100% JSON-serializable for the Vue frontend."""
    if isinstance(obj, dict):
        return {k: clean_payload(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_payload(v) for v in obj]
    elif isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif type(obj).__module__ == 'numpy':
        if hasattr(obj, 'item'):
            val = obj.item()
            return None if isinstance(val, float) and (math.isnan(val) or math.isinf(val)) else val
        return obj
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass
    return obj

def safe_execute(func):
    """Decorator to catch and pipe all Python errors directly to the frontend."""
    @functools.wraps(func)
    def wrapper(req: https_fn.CallableRequest) -> any:
        try:
            result = func(req)
            try:
                json.dumps(result) # Test serialization because Firebase swallows JSON errors
            except Exception:
                err_str = traceback.format_exc()
                return {"status": "error", "message": "JSON Serialization Error in Backend", "traceback": err_str}
            return result
        except Exception as e:
            err_str = traceback.format_exc()
            return {"status": "error", "message": str(e), "traceback": err_str}
    return wrapper

@https_fn.on_call(memory=options.MemoryOption.GB_1, timeout_sec=120, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def get_roster(req: https_fn.CallableRequest) -> any:
    """
    Builds the roster from athlete_info (Firestore) as the single source of truth.
    Joins external systems (HD, Valor) by stored foreign keys, NOT by name.
    """

    # 1. Load athlete_info — this IS the roster
    athlete_info_docs = list(db.collection("athlete_info").stream())
    athletes = []
    for doc in athlete_info_docs:
        d = doc.to_dict()
        d["athlete_uid"] = doc.id
        athletes.append(d)

    if not athletes:
        return {"status": "success", "data": []}

    # Build lookup sets from stored foreign keys
    hd_ids = {str(a["HawkinID"]) for a in athletes if a.get("HawkinID")}
    valor_ids = {str(a["ValorID"]) for a in athletes if a.get("ValorID")}

    # 2. Fetch HD athletes (for name display / validation of links)
    hd_by_id = {}
    try:
        if os.environ.get("HD_TOKEN", "").strip():
            for a in _hd_client().get_athletes(include_inactive=True):
                if a.get("id"):
                    hd_by_id[str(a["id"])] = a.get("name", "")
    except Exception as e:
        print(f"Error fetching HD roster: {e}")

    # 3. Fetch Valor athletes (for name display / validation of links)
    valor_by_id = {}
    try:
        token = get_jwt_token()
        if token:
            valor_endpoint = os.environ.get("VALOR_URL", "").strip().strip("\"'").rstrip("/")
            response = requests.get(f"{valor_endpoint}/athletes", headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 200:
                raw = response.json().get("body", "[]")
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                for a in parsed:
                    fn = (a.get("FirstName") or "").strip()
                    ln = (a.get("LastName") or "").strip()
                    id_col = next((a.get(k) for k in ['ValorID', 'Athlete ID', 'AthleteId', 'athleteId', 'id', 'Id'] if a.get(k)), None)
                    if id_col:
                        valor_by_id[str(id_col)] = f"{fn} {ln}".strip()
    except Exception as e:
        print(f"Error fetching Valor roster: {e}")

    # 4. Check which athletes have Firestore metric data (by athlete_uid)
    sprint_uids = set()
    proagil_uids = set()
    try:
        for doc in db.collection("sprint40").stream():
            uid = doc.to_dict().get("athlete_uid")
            if uid:
                sprint_uids.add(uid)
        for doc in db.collection("pro_agility").stream():
            uid = doc.to_dict().get("athlete_uid")
            if uid:
                proagil_uids.add(uid)
    except Exception as e:
        print(f"Error checking Firestore metric collections: {e}")

    # 5. Build the final roster — all data comes from athlete_info, validated by FK
    roster_list = []
    for a in athletes:
        uid = a.get("athlete_uid")
        hid = str(a["HawkinID"]) if a.get("HawkinID") else None
        vid = str(a["ValorID"]) if a.get("ValorID") else None

        roster_list.append({
            "Name": a.get("Name", ""),
            "athlete_uid": uid,
            "HawkinID": hid if hid and hid in hd_by_id else a.get("HawkinID"),
            "ValorID": vid if vid and vid in valor_by_id else a.get("ValorID"),
            "SwiftID": a.get("SwiftID"),
            "SprintID": uid if uid in sprint_uids else None,
            "ProAgilID": uid if uid in proagil_uids else None,
            "Email": a.get("Email") or a.get("email"),
            "BirthDate": a.get("BirthDate"),
            "Gender": a.get("Gender"),
            "GradYear": a.get("GradYear"),
            "SchoolGrade": a.get("SchoolGrade"),
            "HeightInches": a.get("HeightInches"),
            "LimbDominance": a.get("LimbDominance"),
            "Sports": a.get("Sports"),
            "Positions": a.get("Positions"),
            "CurrentSchool": a.get("CurrentSchool"),
            "SportsTags": a.get("SportsTags") or [],
            "PositionsTags": a.get("PositionsTags") or [],
            "proposed_tags": a.get("proposed_tags"),
        })

    roster_df = pd.DataFrame(roster_list)
    if not roster_df.empty and "Name" in roster_df.columns:
        roster_df = roster_df.sort_values(by="Name")

    raw_data = {
        "status": "success",
        "data": roster_df.to_dict(orient="records")
    }
    return clean_payload(raw_data)

@https_fn.on_call(memory=options.MemoryOption.GB_1, timeout_sec=120, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def get_athlete_metrics(req: https_fn.CallableRequest) -> any:
    """
    Fetches detailed performance data for a specific athlete from Firestore.
    """
    data = req.data
    athlete_uid = data.get("athlete_uid")
    athlete_name = data.get("Name")
    athlete_hawkin_id = data.get("HawkinID")
    athlete_valor_id = data.get("ValorID")
    cohort = data.get("cohort") or "combine"
    # cohort can be:
    #   "combine" — dynamic cohort across all combine athletes (default)
    #   "elite"   — static seeded reference tables
    #   {"type": "sport"|"position"|"age", "value": str} — cohort filtered to athletes
    #               whose tags / age bucket match `value`

    if not athlete_uid:
        return {"status": "error", "message": "No athlete_uid provided"}

    collections = ["sprint40", "pro_agility", "standing_vert", "broad_jump"]
    metrics = {}
    ranks = {}

    for col in collections:
        docs = db.collection(col).where("athlete_uid", "==", athlete_uid).stream()
        # Convert firestore docs to dicts
        metrics[col] = [doc.to_dict() for doc in docs]

    # --- Calculate Percentile Ranks via percentile_engine ---
    from percentile_engine import (
        rank as _rank, best as _best,
        gather_dynamic_cohort_firestore, gather_dynamic_cohort_hd, gather_static_cohort,
    )
    from athlete_tags import age_bucket as _age_bucket

    # --- Resolve cohort to a set of athlete_uids + HawkinIDs (for HD filter) ---
    cohort_label = cohort if isinstance(cohort, str) else f"{cohort.get('type')}:{cohort.get('value')}"
    cohort_athlete_uids = None  # None => no filter (all athletes)
    cohort_hawkin_ids = None
    if isinstance(cohort, dict) and cohort.get("type") in ("sport", "position", "age"):
        ctype = cohort["type"]
        cvalue = (cohort.get("value") or "").lower().strip()
        uids = set()
        hids = set()
        for ad in db.collection("athlete_info").stream():
            ad_d = ad.to_dict()
            if ctype == "sport":
                tags = [t.lower() for t in (ad_d.get("SportsTags") or [])]
                if cvalue in tags:
                    uids.add(ad.id)
                    if ad_d.get("HawkinID"):
                        hids.add(str(ad_d["HawkinID"]))
            elif ctype == "position":
                tags = [t.lower() for t in (ad_d.get("PositionsTags") or [])]
                if cvalue in tags:
                    uids.add(ad.id)
                    if ad_d.get("HawkinID"):
                        hids.add(str(ad_d["HawkinID"]))
            elif ctype == "age":
                if _age_bucket(ad_d.get("BirthDate")) == cvalue:
                    uids.add(ad.id)
                    if ad_d.get("HawkinID"):
                        hids.add(str(ad_d["HawkinID"]))
        cohort_athlete_uids = uids
        cohort_hawkin_ids = hids

    def _build_cohort_combine_firestore(collection_name, extractor):
        """Cohort values: stream collection, filter by athlete_uids if set."""
        if cohort_athlete_uids is None:
            return gather_dynamic_cohort_firestore(db, collection_name, extractor)
        # Filter to specific athlete_uids
        values = []
        for doc in db.collection(collection_name).stream():
            d = doc.to_dict()
            if d.get("athlete_uid") not in cohort_athlete_uids:
                continue
            v = extractor(d)
            if v is not None:
                try:
                    values.append(float(v))
                except (TypeError, ValueError):
                    pass
        return values

    def _build_cohort_hd(hd_tests, field):
        """HD cohort: filter by athlete_id matching cohort_hawkin_ids if set."""
        if not hd_tests:
            return []
        if cohort_hawkin_ids is None:
            return gather_dynamic_cohort_hd(hd_tests, field)
        values = []
        for t in hd_tests:
            if str(t.get("athlete_id") or "") not in cohort_hawkin_ids:
                continue
            v = t.get(field)
            if v is not None:
                try:
                    values.append(float(v))
                except (TypeError, ValueError):
                    pass
        return values

    def _extract_sprint40(d):
        if d.get("Distance") in [40, "40"] and d.get("Total"):
            try: return float(d["Total"])
            except (TypeError, ValueError): return None
        return None

    def _extract_proagility(d):
        if d.get("Distance") in [20, "20"] and d.get("Total"):
            try: return float(d["Total"])
            except (TypeError, ValueError): return None
        return None

    def _extract_vert(d):
        return d.get("VertInches") or d.get("VerticalJump")

    def _extract_broad(d):
        return d.get("BestInches") or d.get("BestBroadJump")

    try:
        # Athlete's own best values
        athlete_sprint = _best(
            [_extract_sprint40(s) for s in metrics.get("sprint40", [])],
            lower_is_better=True,
        )
        athlete_proagil = _best(
            [_extract_proagility(a) for a in metrics.get("pro_agility", [])],
            lower_is_better=True,
        )
        athlete_vert = _best([_extract_vert(v) for v in metrics.get("standing_vert", [])])
        athlete_broad = _best([_extract_broad(b) for b in metrics.get("broad_jump", [])])

        if cohort == "elite":
            # Static seeded reference tables = "Elite Benchmarks" cohort
            sprint_cohort = gather_static_cohort(db, "combine_percentiles", "Sprint40")
            proagil_cohort = gather_static_cohort(db, "combine_percentiles", "ProAgility")
            vert_cohort = gather_static_cohort(db, "combine_percentiles", "VerticalJump")
            broad_cohort = gather_static_cohort(db, "combine_percentiles", "BroadJump")
        else:
            # Dynamic cohort — possibly filtered by athlete cohort_uids
            sprint_cohort = _build_cohort_combine_firestore("sprint40", _extract_sprint40)
            proagil_cohort = _build_cohort_combine_firestore("pro_agility", _extract_proagility)
            vert_cohort = _build_cohort_combine_firestore("standing_vert", _extract_vert)
            broad_cohort = _build_cohort_combine_firestore("broad_jump", _extract_broad)

        ranks["sprint40"] = _rank(athlete_sprint, sprint_cohort, lower_is_better=True, cohort_label=cohort_label)
        ranks["proAgility"] = _rank(athlete_proagil, proagil_cohort, lower_is_better=True, cohort_label=cohort_label)
        ranks["verticalJump"] = _rank(athlete_vert, vert_cohort, cohort_label=cohort_label)
        ranks["broadJump"] = _rank(athlete_broad, broad_cohort, cohort_label=cohort_label)
    except Exception as e:
        print(f"Error calculating combine ranks: {e}")
        
    # Fetch HD Data — join by HawkinID (foreign key), fallback to name
    try:
        if os.environ.get("HD_TOKEN", "").strip() and (athlete_hawkin_id or athlete_name):
            client = _hd_client()
            global hd_cache

            # Date window covering all combine test history through end of next year
            from_ts = int(datetime.datetime(2024, 1, 1).timestamp())
            to_ts = int(datetime.datetime(2027, 12, 31).timestamp())

            def _filter_for_athlete(rows):
                if athlete_hawkin_id:
                    matched = [r for r in rows if str(r.get("athlete_id")) == str(athlete_hawkin_id)]
                    if matched:
                        return matched
                if athlete_name:
                    target = athlete_name.lower().strip()
                    return [r for r in rows if (r.get("athlete_name") or "").lower().strip() == target]
                return []

            # Countermovement Jump — cache only when we successfully resolved a type ID
            if hd_cache["CMJ"] is None:
                cmj_type_id = client.find_test_type_id("CMJ")
                if cmj_type_id:
                    hd_cache["CMJ"] = client.get_tests(test_type_id=cmj_type_id, from_ts=from_ts, to_ts=to_ts)
                # else: leave as None so we retry on the next request (instead of permanently caching [])

            cmj_rows = _filter_for_athlete(hd_cache["CMJ"]) if hd_cache["CMJ"] else []
            if cmj_rows:
                # Athlete's best CMJ values
                best_jh = _best([r.get("jump_height_m") for r in cmj_rows])
                best_mrsi = _best([r.get("mrsi") for r in cmj_rows])

                if cohort == "elite":
                    jh_cohort = gather_static_cohort(db, "fp_percentiles", "JumpHeight")
                    mrsi_cohort = gather_static_cohort(db, "fp_percentiles", "mRSI")
                else:
                    jh_cohort = _build_cohort_hd(hd_cache["CMJ"], "jump_height_m")
                    mrsi_cohort = _build_cohort_hd(hd_cache["CMJ"], "mrsi")

                ranks["fp_jump_height"] = _rank(best_jh, jh_cohort, cohort_label=cohort_label)
                ranks["fp_mrsi"] = _rank(best_mrsi, mrsi_cohort, cohort_label=cohort_label)

                metrics["force_plate_cmj"] = [{
                    "Jump Height (in)": (r["jump_height_m"] * 39.3701) if r.get("jump_height_m") is not None else None,
                    "mRSI": r.get("mrsi"),
                    "Peak Rel Prop Power (W/kg)": r.get("peak_relative_propulsive_power_w_kg"),
                    "Braking Asymmetry": round(r["lr_braking_impulse_index"]) if r.get("lr_braking_impulse_index") is not None else None,
                } for r in cmj_rows]

            # CMJ Rebound — cache only when we successfully resolved a type ID
            if hd_cache["CMJ_REBOUND"] is None:
                cmj_reb_id = client.find_test_type_id("CMJREB")
                if cmj_reb_id:
                    hd_cache["CMJ_REBOUND"] = client.get_tests(test_type_id=cmj_reb_id, from_ts=from_ts, to_ts=to_ts)

            cmj_reb_rows = _filter_for_athlete(hd_cache["CMJ_REBOUND"]) if hd_cache["CMJ_REBOUND"] else []
            if cmj_reb_rows:
                metrics["force_plate_cmj_rebound"] = []
                for r in cmj_reb_rows:
                    # Field names after hawkin_client.normalize_metric_key():
                    #   "Rebound Jump Height(m)" → rebound_jump_height_m
                    #   "Rebound RSI" → rebound_rsi
                    #   "Rebound Stiffness(N/m)" → rebound_stiffness_n_m
                    #   "CMJ Jump Height(m)" → cmj_jump_height_m
                    rebound_jh_m = r.get("rebound_jump_height_m")
                    cmj_jh_m = r.get("cmj_jump_height_m")
                    # Jump Height Ratio = CMJ / Rebound
                    ratio = None
                    if rebound_jh_m and cmj_jh_m:
                        try:
                            ratio = round(float(cmj_jh_m) / float(rebound_jh_m), 3)
                        except Exception:
                            ratio = None

                    metrics["force_plate_cmj_rebound"].append({
                        "Rebound Jump Height (in)": (float(rebound_jh_m) * 39.3701) if rebound_jh_m is not None else None,
                        "Rebound RSI": r.get("rebound_rsi"),
                        "Rebound Stiffness": r.get("rebound_stiffness_n_m"),
                        "Jump Height Ratio": ratio,
                    })

                # CMJ Rebound percentile ranks.
                # No "elite" static table exists for these — only the dynamic combine cohort is meaningful.
                # When cohort='elite' is requested, we still emit the dynamic ranks (best signal we have).
                best_rebound_jh = _best([r.get("rebound_jump_height_m") for r in cmj_reb_rows])
                best_rebound_rsi = _best([r.get("rebound_rsi") for r in cmj_reb_rows])
                # Stiffness is signed (negative N/m); larger magnitude = stiffer.
                # Take the most-negative value as "best" — implemented as min on raw values.
                best_rebound_stiffness = _best(
                    [r.get("rebound_stiffness_n_m") for r in cmj_reb_rows],
                    lower_is_better=True,
                )
                # Jump Height Ratio = CMJ/Rebound; lower = better (rebound goes higher than CMJ).
                ratios = []
                for r in cmj_reb_rows:
                    rj = r.get("rebound_jump_height_m")
                    cj = r.get("cmj_jump_height_m")
                    if rj and cj:
                        try:
                            ratios.append(float(cj) / float(rj))
                        except Exception:
                            pass
                best_ratio = min(ratios) if ratios else None

                # CMJ Rebound has no static elite table — always uses dynamic cohort.
                # If a sport/position/age cohort is selected, filter accordingly.
                jh_cohort_r = _build_cohort_hd(hd_cache["CMJ_REBOUND"], "rebound_jump_height_m")
                rsi_cohort_r = _build_cohort_hd(hd_cache["CMJ_REBOUND"], "rebound_rsi")
                stiff_cohort_r = _build_cohort_hd(hd_cache["CMJ_REBOUND"], "rebound_stiffness_n_m")
                ratio_cohort_r = []
                cohort_tests = (
                    [t for t in (hd_cache["CMJ_REBOUND"] or []) if str(t.get("athlete_id") or "") in cohort_hawkin_ids]
                    if cohort_hawkin_ids is not None
                    else (hd_cache["CMJ_REBOUND"] or [])
                )
                for t in cohort_tests:
                    rj, cj = t.get("rebound_jump_height_m"), t.get("cmj_jump_height_m")
                    if rj and cj:
                        try:
                            ratio_cohort_r.append(float(cj) / float(rj))
                        except Exception:
                            pass

                # For CMJ Rebound, label always reflects the requested cohort
                # ('elite' falls through to dynamic since no static table exists).
                rebound_label = cohort_label if cohort != "elite" else "combine"
                ranks["cmj_rebound_jump_height"] = _rank(best_rebound_jh, jh_cohort_r, cohort_label=rebound_label)
                ranks["cmj_rebound_rsi"] = _rank(best_rebound_rsi, rsi_cohort_r, cohort_label=rebound_label)
                ranks["cmj_rebound_stiffness"] = _rank(best_rebound_stiffness, stiff_cohort_r, lower_is_better=True, cohort_label=rebound_label)
                ranks["cmj_rebound_jump_height_ratio"] = _rank(best_ratio, ratio_cohort_r, lower_is_better=True, cohort_label=rebound_label)

            # Debug info to help diagnose missing data per athlete
            metrics["_hd_debug"] = {
                "athlete_hawkin_id": athlete_hawkin_id,
                "athlete_name_query": athlete_name,
                "cmj_total_in_window": len(hd_cache["CMJ"] or []),
                "cmj_matched_for_athlete": len(cmj_rows) if hd_cache["CMJ"] else None,
                "cmj_rebound_total_in_window": len(hd_cache["CMJ_REBOUND"] or []),
                "cmj_rebound_matched_for_athlete": len(cmj_reb_rows) if hd_cache["CMJ_REBOUND"] else None,
                "cmj_rebound_sample_keys": list(cmj_reb_rows[0].keys()) if cmj_reb_rows else None,
            }
    except Exception as e:
        print(f"Error fetching HD metrics: {e}")
        metrics["_hd_debug"] = {"error": str(e)}
        
    # Fetch Valor Movement Data
    metrics["valor"] = {"Shoulder": 0, "Ankle": 0, "Hip": 0}
    try:
        if athlete_valor_id:
            token = get_jwt_token()
            if token:
                valor_endpoint = os.environ.get("VALOR_URL", "").strip().strip("\"'").rstrip("/")
                headers = {"Authorization": f"Bearer {token}"}

                global valor_cache
                if valor_cache["sessions"] is None:
                    # Fetch sessions across multiple pages, no date filter (include all historical sessions)
                    all_items = []
                    continuation_token = '""'
                    for _ in range(10):  # Up to 10 pages
                        req_headers = {**headers, 'X-Continuation-Token': continuation_token}
                        res = requests.get(f"{valor_endpoint}/sessions", headers=req_headers)
                        if res.status_code == 200:
                            jdata = res.json()
                            body = jdata.get("body", "[]")
                            all_items.extend(json.loads(body) if isinstance(body, str) else body)
                            continuation_token = jdata.get("X-Continuation-Token")
                            if not continuation_token or continuation_token == "null":
                                break
                        else:
                            break
                    valor_cache["sessions"] = pd.DataFrame(all_items)

                sess_df = valor_cache["sessions"]
                if sess_df is not None and not sess_df.empty and 'Athlete ID' in sess_df.columns:
                    athlete_sessions = sess_df[sess_df['Athlete ID'].astype(str) == str(athlete_valor_id)]

                    def get_score(session_names):
                        if athlete_sessions.empty or 'Session Name' not in athlete_sessions.columns:
                            return 0
                        keys = athlete_sessions[athlete_sessions['Session Name'].isin(session_names)]['s3Key'].tolist()
                        scores = []
                        for k in keys:
                            res = requests.get(f"{valor_endpoint}/reportData", headers=headers, params={"s3Key": k})
                            if res.status_code == 200:
                                jdata = res.json()
                                body = jdata.get("body", "{}")
                                if isinstance(body, str):
                                    body = json.loads(body)
                                scores.append(extract_valor_score(body))
                        return round(float(np.mean(scores)), 1) if scores else 0

                    metrics["valor"]["Ankle"] = get_score(["Left Regular Ankle Dorsiflexion - Weighted", "Right Regular Ankle Dorsiflexion - Weighted"])
                    metrics["valor"]["Shoulder"] = get_score(["Left 90-90 Test Unilateral Shoulder IR/ER", "Right 90-90 Test Unilateral Shoulder IR/ER"])
                    metrics["valor"]["Hip"] = get_score(["Hip Hinge Test"])
    except Exception as e:
        print(f"Error fetching Valor metrics: {e}")

    metrics["ranks"] = ranks

    raw_data = {
        "status": "success",
        "data": metrics
    }
    return clean_payload(raw_data)

@https_fn.on_call(memory=options.MemoryOption.GB_1, timeout_sec=120, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def set_user_role(req: https_fn.CallableRequest) -> any:
    """Admin only endpoint to set RBAC roles and link athlete names to auth accounts."""
    if not req.auth or not req.auth.uid:
        return {"status": "error", "message": "Unauthenticated caller"}
        
    caller = firebase_auth.get_user(req.auth.uid)
    if caller.custom_claims is None or caller.custom_claims.get("role") != "admin":
        return {"status": "error", "message": "Permission denied. Admins only."}
        
    target_email = req.data.get("email")
    target_role = req.data.get("role")
    athlete_name = req.data.get("athlete_name")
    
    target_user = firebase_auth.get_user_by_email(target_email)
    new_claims = {"role": target_role}
    if target_role == "athlete" and athlete_name:
        new_claims["athlete_name"] = athlete_name
        
    firebase_auth.set_custom_user_claims(target_user.uid, new_claims)
    return {"status": "success", "message": f"Successfully updated {target_email} to {target_role}."}

@https_fn.on_call(memory=options.MemoryOption.GB_1, timeout_sec=120, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def parse_birthdate(s):
    """Match an athlete's birth date across format variants:
    '2010-08-15', '08-2010', '8/15/2010', etc. Returns (month, year) or None."""
    if not s:
        return None
    s = str(s).strip()
    # Try ISO YYYY-MM-DD
    import re as _re
    m = _re.match(r"^(\d{4})-(\d{1,2})-\d{1,2}$", s)
    if m:
        return (int(m.group(2)), int(m.group(1)))
    # Try MM-YYYY (existing data style)
    m = _re.match(r"^(\d{1,2})-(\d{4})$", s)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    # Try MM/DD/YYYY
    m = _re.match(r"^(\d{1,2})/\d{1,2}/(\d{4})$", s)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    # Try YYYY/MM/DD
    m = _re.match(r"^(\d{4})/(\d{1,2})/\d{1,2}$", s)
    if m:
        return (int(m.group(2)), int(m.group(1)))
    return None


@https_fn.on_call(memory=options.MemoryOption.MB_512, timeout_sec=60, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def register_athlete(req: https_fn.CallableRequest) -> any:
    """Public endpoint for an athlete to verify their identity and create login.

    Flow: athlete provides email + birthdate → we match against athlete_info →
    if match, create Firebase Auth user with role:athlete custom claim and send
    a password reset email so they can set their own password.
    """
    email = req.data.get("email", "").strip()
    birth_date = req.data.get("birthDate", "").strip()

    if not email or not birth_date:
        return {"status": "error", "message": "Email and birth date are required."}

    target_month_year = parse_birthdate(birth_date)
    if not target_month_year:
        return {"status": "error", "message": "Could not parse birth date. Use YYYY-MM-DD format."}

    email_lower = email.lower()

    # Find athlete_info by email (case-insensitive)
    matched = None
    matched_id = None
    for doc in db.collection("athlete_info").stream():
        d = doc.to_dict()
        doc_email = d.get("Email") or d.get("email")
        if doc_email and str(doc_email).strip().lower() == email_lower:
            matched = d
            matched_id = doc.id
            break

    if not matched:
        return {
            "status": "error",
            "code": "email_not_found",
            "message": "We couldn't find an athlete with that email. If you don't have an email on file, request admin verification.",
        }

    # Verify birth date (month + year must match)
    stored_birth = matched.get("BirthDate") or ""
    stored_my = parse_birthdate(stored_birth)
    if not stored_my or stored_my != target_month_year:
        return {
            "status": "error",
            "code": "birth_mismatch",
            "message": "The birth date doesn't match our records. Please double-check.",
        }

    athlete_name = matched.get("Name", "")

    # Check if Firebase Auth user already exists for this email
    try:
        existing = firebase_auth.get_user_by_email(email)
        # Already exists — just (re)send password reset link
        link = firebase_auth.generate_password_reset_link(email)
        return {
            "status": "exists",
            "message": "An account already exists. Use 'Forgot password' to reset, or sign in directly.",
            "athlete_name": athlete_name,
            "reset_link": link,
        }
    except firebase_auth.UserNotFoundError:
        pass

    # Create Firebase Auth user with a placeholder password — they'll reset it
    import secrets
    temp_password = secrets.token_urlsafe(24)

    try:
        user = firebase_auth.create_user(email=email, password=temp_password, email_verified=False)
        firebase_auth.set_custom_user_claims(user.uid, {"role": "athlete", "athlete_name": athlete_name})

        # Generate password reset link (sent by client via Firebase Auth SDK)
        reset_link = firebase_auth.generate_password_reset_link(email)

        # Stamp athlete_info with the auth uid
        if matched_id:
            db.collection("athlete_info").document(matched_id).update({"auth_uid": user.uid})

        return {
            "status": "success",
            "message": f"Verified! Check your email at {email} to set your password.",
            "athlete_name": athlete_name,
            "reset_link": reset_link,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to create account: {str(e)}"}


@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=30, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def request_admin_verification(req: https_fn.CallableRequest) -> any:
    """Public endpoint: athlete with no email on file requests admin add their email.
    Writes to admin_requests collection for admin review."""
    name = req.data.get("name", "").strip()
    email = req.data.get("email", "").strip()
    birth_date = req.data.get("birthDate", "").strip()
    message = req.data.get("message", "").strip()

    if not name or not email:
        return {"status": "error", "message": "Name and email are required."}

    db.collection("admin_requests").add({
        "type": "athlete_verification",
        "name": name,
        "email": email,
        "birthDate": birth_date,
        "message": message,
        "status": "pending",
        "created_at": firestore.SERVER_TIMESTAMP,
    })

    return {"status": "success", "message": "Request received. An admin will review and contact you shortly."}


@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=30, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def list_admin_requests(req: https_fn.CallableRequest) -> any:
    """Admin/coach only: list pending verification requests."""
    caller_uid, err = _require_staff(req)
    if err:
        return err

    requests_out = []
    for doc in db.collection("admin_requests").where("status", "==", "pending").stream():
        d = doc.to_dict()
        d["id"] = doc.id
        # Convert timestamp to iso string for JSON
        ts = d.get("created_at")
        if ts and hasattr(ts, "isoformat"):
            d["created_at"] = ts.isoformat()
        requests_out.append(d)

    # Sort by newest first
    requests_out.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return {"status": "success", "data": requests_out}


@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=30, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def resolve_admin_request(req: https_fn.CallableRequest) -> any:
    """Admin only: approve or reject a pending request.
    On approve with athlete_uid, links the request's email to that athlete_info doc."""
    caller_uid, err = _require_staff(req)
    if err:
        return err
    caller = firebase_auth.get_user(caller_uid)
    if (caller.custom_claims or {}).get("role") != "admin":
        return {"status": "error", "message": "Admin only."}

    request_id = req.data.get("request_id")
    action = req.data.get("action")  # 'approve' or 'reject'
    athlete_uid = req.data.get("athlete_uid")  # required if approving

    if not request_id or action not in ("approve", "reject"):
        return {"status": "error", "message": "request_id and action ('approve'|'reject') required."}

    request_ref = db.collection("admin_requests").document(request_id)
    snap = request_ref.get()
    if not snap.exists:
        return {"status": "error", "message": "Request not found."}
    request_data = snap.to_dict()

    if action == "approve":
        if not athlete_uid:
            return {"status": "error", "message": "athlete_uid required to approve."}
        # Update athlete_info with the email
        db.collection("athlete_info").document(athlete_uid).update({
            "Email": request_data.get("email"),
        })

    request_ref.update({
        "status": "approved" if action == "approve" else "rejected",
        "resolved_by": caller_uid,
        "resolved_at": firestore.SERVER_TIMESTAMP,
        "linked_athlete_uid": athlete_uid if action == "approve" else None,
    })

    return {"status": "success", "message": f"Request {action}d."}

@https_fn.on_call(memory=options.MemoryOption.GB_1, timeout_sec=120, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def admin_create_user(req: https_fn.CallableRequest) -> any:
    """Admin only endpoint to create new coach or admin users directly."""
    if not req.auth or not req.auth.uid:
        return {"status": "error", "message": "Unauthenticated caller"}
        
    caller = firebase_auth.get_user(req.auth.uid)
    if caller.custom_claims is None or caller.custom_claims.get("role") != "admin":
        return {"status": "error", "message": "Permission denied. Admins only."}
        
    email = req.data.get("email")
    password = req.data.get("password")
    role = req.data.get("role")
    athlete_name = req.data.get("athlete_name")
    
    try:
        user = firebase_auth.create_user(email=email, password=password)
        new_claims = {"role": role}
        if role == "athlete" and athlete_name:
            new_claims["athlete_name"] = athlete_name
            
        firebase_auth.set_custom_user_claims(user.uid, new_claims)
        return {"status": "success", "message": f"Successfully created {role} account for {email}."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@https_fn.on_call(memory=options.MemoryOption.GB_1, timeout_sec=120, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def upload_roster_csv(req: https_fn.CallableRequest) -> any:
    """Admin only endpoint to upload a CSV and update the athlete_info roster."""
    if not req.auth or not req.auth.uid:
        return {"status": "error", "message": "Unauthenticated caller"}
        
    caller = firebase_auth.get_user(req.auth.uid)
    if caller.custom_claims is None or caller.custom_claims.get("role") != "admin":
        return {"status": "error", "message": "Permission denied. Admins only."}
        
    csv_text = req.data.get("csv_data")
    if not csv_text:
        return {"status": "error", "message": "No CSV data provided."}
        
    try:
        df = pd.read_csv(io.StringIO(csv_text))
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")
        
        # Get existing athletes to map Name -> doc_id for upserts (prevents duplicates)
        existing_docs = db.collection("athlete_info").stream()
        name_to_id = {doc.to_dict().get("Name"): doc.id for doc in existing_docs if doc.to_dict().get("Name")}
        
        batch = db.batch()
        collection_ref = db.collection("athlete_info")
        count = 0
        
        for record in records:
            name = record.get("Name")
            if not name:
                continue # Skip empty rows
            
            if name in name_to_id:
                # Update existing athlete
                doc_ref = collection_ref.document(name_to_id[name])
                batch.set(doc_ref, record, merge=True)
            else:
                # Create new athlete
                doc_ref = collection_ref.document()
                batch.set(doc_ref, record)
                
            count += 1
            # Firestore limits batches to 500 writes
            if count % 400 == 0:
                batch.commit()
                batch = db.batch()
                
        batch.commit()
        return {"status": "success", "message": f"Successfully processed {count} roster records."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse or upload CSV: {str(e)}"}

@https_fn.on_call(memory=options.MemoryOption.GB_1, timeout_sec=300, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def upload_swift_csv(req: https_fn.CallableRequest) -> any:
    """Parse a Swift timing CSV and write splits to sprint40/pro_agility collections."""
    caller_uid, err = _require_staff(req)
    if err:
        return err

    csv_text = req.data.get("csv_data")
    if not csv_text:
        return {"status": "error", "message": "No CSV data provided."}

    try:
        df = pd.read_csv(io.StringIO(csv_text))
        df = df.where(pd.notnull(df), None)
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse CSV: {str(e)}"}

    # Normalize column names (Swift CSV has typo "AcitivityTitle")
    col_map = {}
    for c in df.columns:
        if c.lower().replace(" ", "") in ["acitivitytitle", "activitytitle"]:
            col_map[c] = "ActivityTitle"
    if col_map:
        df = df.rename(columns=col_map)

    required_cols = {"AthleteId", "FirstName", "LastName", "ActivityTitle", "ActivityIdentifier",
                     "ActivityTimestamp", "Sequence", "Total", "Split", "Distance", "Velocity"}
    missing = required_cols - set(df.columns)
    if missing:
        return {"status": "error", "message": f"Missing columns: {', '.join(missing)}"}

    # Map ActivityTitle to Firestore collection
    TITLE_MAP = {
        "SLO CC 10 + 30": "sprint40",
        "Pro Shuttle Steady": "pro_agility",
    }

    # Build Swift athlete lookup: SwiftID -> athlete_uid from athlete_info
    athlete_docs = list(db.collection("athlete_info").stream())
    swift_to_uid = {}   # SwiftID -> athlete_uid
    name_to_uid = {}    # normalized "first last" -> (athlete_uid, doc_id)
    for doc in athlete_docs:
        d = doc.to_dict()
        uid = doc.id
        if d.get("SwiftID"):
            swift_to_uid[str(d["SwiftID"])] = uid
        name = (d.get("Name") or "").strip().lower()
        if name:
            name_to_uid[name] = uid

    batch = db.batch()
    count = 0
    skipped = 0
    unmatched_athletes = set()
    new_swift_links = {}  # athlete_uid -> SwiftID (to update athlete_info)

    for _, row in df.iterrows():
        title = str(row.get("ActivityTitle") or "").strip()
        collection_name = TITLE_MAP.get(title)
        if not collection_name:
            skipped += 1
            continue

        # Skip Sequence=0 rows (initialization with all zeros)
        seq = row.get("Sequence")
        if seq is not None and (seq == 0 or str(seq) == "0"):
            continue

        swift_id = str(row.get("AthleteId") or "").strip()
        first = str(row.get("FirstName") or "").strip()
        middle = str(row.get("MiddleName") or "").strip()
        last = str(row.get("LastName") or "").strip()
        full_name = f"{first} {last}".strip()

        # Resolve athlete_uid: FK first, then name match
        athlete_uid = swift_to_uid.get(swift_id)
        if not athlete_uid:
            athlete_uid = name_to_uid.get(full_name.lower())
        if not athlete_uid:
            # Try with middle name
            full_with_middle = f"{first} {middle} {last}".strip() if middle else ""
            if full_with_middle:
                athlete_uid = name_to_uid.get(full_with_middle.lower())

        if not athlete_uid:
            unmatched_athletes.add(full_name)
            continue

        # Track new Swift ID links
        if swift_id and swift_id not in swift_to_uid:
            swift_to_uid[swift_id] = athlete_uid
            new_swift_links[athlete_uid] = swift_id

        doc_data = {
            "athlete_uid": athlete_uid,
            "Name": full_name,
            "SwiftID": swift_id,
            "ActivityIdentifier": str(row.get("ActivityIdentifier") or ""),
            "ActivityTimestamp": str(row.get("ActivityTimestamp") or ""),
            "Sequence": int(row["Sequence"]) if row.get("Sequence") is not None else None,
            "Total": float(row["Total"]) if row.get("Total") is not None else None,
            "Split": float(row["Split"]) if row.get("Split") is not None else None,
            "Distance": float(row["Distance"]) if row.get("Distance") is not None else None,
            "Velocity": float(row["Velocity"]) if row.get("Velocity") is not None else None,
        }

        doc_ref = db.collection(collection_name).document()
        batch.set(doc_ref, doc_data)
        count += 1

        if count % 400 == 0:
            batch.commit()
            batch = db.batch()

    # Save new Swift ID links to athlete_info
    for uid, sid in new_swift_links.items():
        batch.update(db.collection("athlete_info").document(uid), {"SwiftID": sid})

    batch.commit()

    result = {
        "status": "success",
        "message": f"Imported {count} split records.",
        "imported": count,
        "skipped_unknown_activity": skipped,
        "new_swift_links": len(new_swift_links),
    }
    if unmatched_athletes:
        result["unmatched_athletes"] = sorted(list(unmatched_athletes))
        result["message"] += f" {len(unmatched_athletes)} athlete(s) could not be matched."

    return result


@https_fn.on_call(memory=options.MemoryOption.GB_1, timeout_sec=120, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def update_athlete_info(req: https_fn.CallableRequest) -> any:
    """Endpoint for admins/coaches to edit an athlete's profile."""
    if not req.auth or not req.auth.uid:
        return {"status": "error", "message": "Unauthenticated caller"}
        
    caller = firebase_auth.get_user(req.auth.uid)
    role = caller.custom_claims.get("role") if caller.custom_claims else "athlete"
    if role not in ["admin", "coach"]:
        return {"status": "error", "message": "Permission denied. Admins or Coaches only."}
        
    data = req.data
    uid = data.get("athlete_uid")
    
    update_data = {}
    for key in ["Name", "Email", "BirthDate", "Gender", "GradYear", "SchoolGrade", "HeightInches", "LimbDominance", "Sports", "Positions", "CurrentSchool", "ValorID", "HawkinID", "SwiftID"]:
        if key in data:
            update_data[key] = data[key]
    # Array fields (tags). Accept either an array or a comma-separated string for ergonomic POSTs.
    for key in ["SportsTags", "PositionsTags"]:
        if key in data:
            val = data[key]
            if isinstance(val, str):
                val = [t.strip() for t in val.split(",") if t.strip()]
            elif not isinstance(val, list):
                val = []
            update_data[key] = val
            
    if not uid:
        doc_ref = db.collection("athlete_info").document()
        uid = doc_ref.id
        update_data["athlete_uid"] = uid
        doc_ref.set(update_data)
    else:
        db.collection("athlete_info").document(uid).set(update_data, merge=True)
        
    return {"status": "success", "message": "Successfully updated athlete info.", "athlete_uid": uid}


# ──────────────────────────────────────────────
# Data Collection Dashboard
# ──────────────────────────────────────────────

@https_fn.on_call(memory=options.MemoryOption.MB_512, timeout_sec=60, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def get_data_dashboard(req: https_fn.CallableRequest) -> any:
    """Return per-collection data ingestion stats: total count, last write,
    counts for last 24h/7d/30d. Helps verify data is actually being collected."""
    caller_uid, err = _require_staff(req)
    if err:
        return err

    now = datetime.datetime.now(datetime.timezone.utc)
    day_ago = now - datetime.timedelta(days=1)
    week_ago = now - datetime.timedelta(days=7)
    month_ago = now - datetime.timedelta(days=30)

    def _to_dt(ts):
        """Coerce Firestore timestamp / ISO string / DD/MM/YYYY string to datetime."""
        if ts is None:
            return None
        # Firestore Timestamp (DatetimeWithNanoseconds)
        if hasattr(ts, "timestamp") and not isinstance(ts, str):
            try:
                return ts if ts.tzinfo else ts.replace(tzinfo=datetime.timezone.utc)
            except Exception:
                pass
        s = str(ts).strip()
        # ISO 8601 (e.g. "2026-05-09T10:00:00-07:00")
        try:
            return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            pass
        # Swift's "DD/MM/YYYYTHH:MM:SS AM" format
        import re as _re
        m = _re.match(r"^(\d{2})/(\d{2})/(\d{4})T(\d{2}):(\d{2}):(\d{2})\s*(AM|PM)?", s)
        if m:
            try:
                day, mo, yr, hh, mm, ss, ampm = m.groups()
                hh = int(hh)
                if ampm == "PM" and hh < 12:
                    hh += 12
                if ampm == "AM" and hh == 12:
                    hh = 0
                return datetime.datetime(int(yr), int(mo), int(day), hh, int(mm), int(ss), tzinfo=datetime.timezone.utc)
            except Exception:
                pass
        return None

    def _summarize(collection_name, ts_field):
        total = 0
        last_24h = 0
        last_7d = 0
        last_30d = 0
        latest_dt = None
        latest_raw = None
        try:
            for doc in db.collection(collection_name).stream():
                d = doc.to_dict()
                total += 1
                ts_raw = d.get(ts_field)
                dt = _to_dt(ts_raw)
                if dt:
                    if dt > day_ago:
                        last_24h += 1
                    if dt > week_ago:
                        last_7d += 1
                    if dt > month_ago:
                        last_30d += 1
                    if latest_dt is None or dt > latest_dt:
                        latest_dt = dt
                        latest_raw = ts_raw
        except Exception as e:
            return {"error": str(e)}

        return {
            "total": total,
            "last_24h": last_24h,
            "last_7d": last_7d,
            "last_30d": last_30d,
            "latest": latest_dt.isoformat() if latest_dt else None,
            "latest_raw": str(latest_raw) if latest_raw else None,
            "ts_field": ts_field,
        }

    collections = {
        "standing_reach": _summarize("standing_reach", "recorded_at"),
        "standing_vert": _summarize("standing_vert", "recorded_at"),
        "broad_jump": _summarize("broad_jump", "recorded_at"),
        "sprint40": _summarize("sprint40", "ActivityTimestamp"),
        "pro_agility": _summarize("pro_agility", "ActivityTimestamp"),
        "athlete_summaries": _summarize("athlete_summaries", "created_at"),
    }

    # Athlete count + how many have email
    athlete_total = 0
    athletes_with_email = 0
    athletes_with_hd = 0
    athletes_with_valor = 0
    athletes_with_swift = 0
    for doc in db.collection("athlete_info").stream():
        d = doc.to_dict()
        athlete_total += 1
        if d.get("Email"):
            athletes_with_email += 1
        if d.get("HawkinID"):
            athletes_with_hd += 1
        if d.get("ValorID"):
            athletes_with_valor += 1
        if d.get("SwiftID"):
            athletes_with_swift += 1

    return {
        "status": "success",
        "generated_at": now.isoformat(),
        "collections": collections,
        "athlete_info": {
            "total": athlete_total,
            "with_email": athletes_with_email,
            "with_hd": athletes_with_hd,
            "with_valor": athletes_with_valor,
            "with_swift": athletes_with_swift,
        },
    }


# ──────────────────────────────────────────────
# Backfill: sync historic Swift IDs onto athlete_info
# ──────────────────────────────────────────────

@https_fn.on_call(memory=options.MemoryOption.MB_512, timeout_sec=300, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def backfill_athlete_tags(req: https_fn.CallableRequest) -> any:
    """Propose SportsTags and PositionsTags for every athlete based on substring
    matching against the curated taxonomy in athlete_tags.py. Writes proposed
    arrays to a `proposed_tags` field so admin can review without overwriting
    curated values. Safe to re-run."""
    caller_uid, err = _require_staff(req)
    if err:
        return err

    from athlete_tags import propose_sports_tags, propose_position_tags

    proposed = 0
    skipped = 0
    examples = []
    for doc in db.collection("athlete_info").stream():
        d = doc.to_dict()
        sports = propose_sports_tags(d.get("Sports"))
        positions = propose_position_tags(d.get("Positions"), sports)
        if not sports and not positions:
            skipped += 1
            continue
        doc.reference.update({
            "proposed_tags": {
                "SportsTags": sports,
                "PositionsTags": positions,
                "generated_at": firestore.SERVER_TIMESTAMP,
            }
        })
        proposed += 1
        if len(examples) < 8:
            examples.append({
                "name": d.get("Name"),
                "sports_text": d.get("Sports"),
                "positions_text": d.get("Positions"),
                "proposed_sports": sports,
                "proposed_positions": positions,
            })

    return {
        "status": "success",
        "summary": f"Proposed tags for {proposed} athletes ({skipped} had no matchable text).",
        "proposed": proposed,
        "skipped": skipped,
        "examples": examples,
    }


@https_fn.on_call(memory=options.MemoryOption.MB_512, timeout_sec=300, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def backfill_swift_ids(req: https_fn.CallableRequest) -> any:
    """Walk sprint40 and pro_agility docs, extract Swift AthleteId,
    and write back to athlete_info.SwiftID for any athlete missing one."""
    caller_uid, err = _require_staff(req)
    if err:
        return err

    # Build athlete_uid -> swift_id map from existing test data
    athlete_uid_to_swift = {}
    for col in ["sprint40", "pro_agility"]:
        for doc in db.collection(col).stream():
            d = doc.to_dict()
            uid = d.get("athlete_uid")
            if not uid:
                continue
            swift_id = d.get("SwiftID") or d.get("AthleteId") or d.get("athlete_id")
            if swift_id and uid not in athlete_uid_to_swift:
                athlete_uid_to_swift[uid] = str(swift_id)

    # For each, check athlete_info and update if missing
    updated = []
    already_set = []
    orphans = []
    no_swift_in_data = []

    for uid, swift_id in athlete_uid_to_swift.items():
        doc_ref = db.collection("athlete_info").document(uid)
        snap = doc_ref.get()
        if not snap.exists:
            orphans.append(uid)
            continue
        existing = snap.to_dict()
        if existing.get("SwiftID"):
            already_set.append(existing.get("Name") or uid)
        else:
            doc_ref.update({"SwiftID": swift_id})
            updated.append(existing.get("Name") or uid)

    # Athletes in athlete_info that have no SwiftID and no entry in our map
    for doc in db.collection("athlete_info").stream():
        uid = doc.id
        d = doc.to_dict()
        if not d.get("SwiftID") and uid not in athlete_uid_to_swift:
            no_swift_in_data.append(d.get("Name") or uid)

    return {
        "status": "success",
        "updated": updated,
        "already_set": already_set,
        "orphans_in_test_data": orphans,
        "athletes_without_swift_data": no_swift_in_data,
        "summary": f"Linked {len(updated)} athletes. {len(already_set)} were already linked. {len(orphans)} sprint/agility records reference missing athletes. {len(no_swift_in_data)} athletes have no Swift test data.",
    }


# ──────────────────────────────────────────────
# Diagnostics
# ──────────────────────────────────────────────

@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=30, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def check_valor_connection(req: https_fn.CallableRequest) -> any:
    """Admin diagnostic: test Valor API connection step by step."""
    if not req.auth or not req.auth.uid:
        return {"status": "error", "message": "Unauthenticated"}
    caller = firebase_auth.get_user(req.auth.uid)
    if (caller.custom_claims or {}).get("role") not in ["admin", "coach"]:
        return {"status": "error", "message": "Admin/Coach only"}

    result = {"steps": []}

    # Step 1: Check env vars
    valor_url = os.environ.get("VALOR_URL", "").strip().strip("\"'")
    username = os.environ.get("VALOR_USER", "").strip().strip("\"'")
    client_id = os.environ.get("VALOR_CLIENT_ID", "").strip().strip("\"'")
    token_url = os.environ.get("VALOR_TOKEN_URL", "").strip().strip("\"'")
    has_password = bool(os.environ.get("VALOR_PASSWORD", "").strip())

    result["steps"].append({
        "step": "Environment variables",
        "VALOR_URL": valor_url or "MISSING",
        "VALOR_USER": username or "MISSING",
        "VALOR_CLIENT_ID": client_id or "MISSING",
        "VALOR_TOKEN_URL": token_url or "MISSING",
        "VALOR_PASSWORD": "SET" if has_password else "MISSING",
    })

    if not all([valor_url, username, client_id, token_url, has_password]):
        result["status"] = "error"
        result["message"] = "Missing environment variables"
        return result

    # Step 2: JWT auth — try manually to capture the actual error
    password = os.environ.get("VALOR_PASSWORD", "").strip().strip("\"'")
    auth_payload = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": client_id,
        "AuthParameters": {"USERNAME": username, "PASSWORD": password}
    }
    auth_headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"
    }
    try:
        auth_response = requests.post(token_url, json=auth_payload, headers=auth_headers, timeout=10)
        result["steps"].append({
            "step": "JWT Auth",
            "status_code": auth_response.status_code,
            "response": auth_response.text[:500] if auth_response.status_code != 200 else "OK",
        })
        if auth_response.status_code != 200:
            result["status"] = "error"
            result["message"] = f"Cognito auth failed ({auth_response.status_code})"
            return result
    except Exception as e:
        result["steps"].append({"step": "JWT Auth", "status": "EXCEPTION", "detail": str(e)})
        result["status"] = "error"
        result["message"] = str(e)
        return result

    token = auth_response.json().get("AuthenticationResult", {}).get("IdToken")
    if not token:
        result["steps"].append({"step": "JWT Token Extract", "status": "FAILED", "detail": "No IdToken in response", "response_keys": list(auth_response.json().keys())})
        result["status"] = "error"
        result["message"] = "No IdToken in Cognito response"
        return result

    result["steps"].append({"step": "JWT Token", "status": "OK", "preview": token[:20] + "..."})

    # Step 3: Fetch athletes
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{valor_url.rstrip('/')}/athletes", headers=headers, timeout=15)
        result["steps"].append({
            "step": "GET /athletes",
            "status_code": response.status_code,
            "response_keys": list(response.json().keys()) if response.status_code == 200 else None,
            "response_preview": str(response.text[:300]) if response.status_code != 200 else None,
        })

        if response.status_code == 200:
            raw = response.json()
            body = raw.get("body", "[]")
            parsed = json.loads(body) if isinstance(body, str) else body
            result["steps"].append({
                "step": "Parse athletes",
                "type_of_body": type(body).__name__,
                "athlete_count": len(parsed) if isinstance(parsed, list) else "NOT_A_LIST",
                "sample": parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else None,
            })
            result["status"] = "success"
            result["message"] = f"Connected. {len(parsed)} athletes found."
        else:
            result["status"] = "error"
            result["message"] = f"API returned {response.status_code}"
    except Exception as e:
        result["steps"].append({"step": "GET /athletes", "status": "EXCEPTION", "detail": str(e)})
        result["status"] = "error"
        result["message"] = str(e)

    return result


# ──────────────────────────────────────────────
# HD athlete management (matching, create, update)
# ──────────────────────────────────────────────

@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=60, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def get_hd_athletes(req: https_fn.CallableRequest) -> any:
    """Returns the list of athletes from Hawkin Dynamics for the matching UI."""
    caller_uid, err = _require_staff(req)
    if err:
        return err

    if not os.environ.get("HD_TOKEN", "").strip():
        return {"status": "error", "message": "HD_TOKEN not configured."}

    hd_athletes_raw = _hd_client().get_athletes(include_inactive=True)
    if not hd_athletes_raw:
        return {"status": "success", "data": []}

    athletes = [{
        "HawkinID": str(a["id"]),
        "Name": str(a.get("name", "")),
        "active": bool(a.get("active", True)),
    } for a in hd_athletes_raw if a.get("id")]

    # Mark which are already assigned in Firestore
    assigned_ids = set()
    for doc in db.collection("athlete_info").stream():
        hid = doc.to_dict().get("HawkinID")
        if hid:
            assigned_ids.add(str(hid))

    for a in athletes:
        a["assigned"] = a["HawkinID"] in assigned_ids

    return {"status": "success", "data": athletes}


@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=60, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def link_hd_athlete(req: https_fn.CallableRequest) -> any:
    """Link a roster athlete to an HD athlete and push the Bookeo name to HD."""
    caller_uid, err = _require_staff(req)
    if err:
        return err

    athlete_uid = req.data.get("athlete_uid")
    hawkin_id = req.data.get("hawkin_id")
    bookeo_name = req.data.get("bookeo_name")

    if not athlete_uid or not hawkin_id:
        return {"status": "error", "message": "athlete_uid and hawkin_id required."}

    # 1. Store HawkinID on athlete_info
    db.collection("athlete_info").document(athlete_uid).set({"HawkinID": hawkin_id}, merge=True)

    # 2. Push the Bookeo name to HD to fix spelling
    if bookeo_name:
        try:
            if os.environ.get("HD_TOKEN", "").strip():
                _hd_client().update_athlete(hawkin_id, name=bookeo_name, active=True)
        except Exception as e:
            return {"status": "warning", "message": f"Linked in Firestore but HD update failed: {str(e)}"}

    return {"status": "success", "message": f"Linked and updated HD name to '{bookeo_name}'."}


@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=60, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def create_hd_athlete(req: https_fn.CallableRequest) -> any:
    """Create a new athlete in Hawkin Dynamics from Bookeo data and link to roster."""
    caller_uid, err = _require_staff(req)
    if err:
        return err

    athlete_uid = req.data.get("athlete_uid")
    name = req.data.get("name")

    if not athlete_uid or not name:
        return {"status": "error", "message": "athlete_uid and name required."}

    if not os.environ.get("HD_TOKEN", "").strip():
        return {"status": "error", "message": "HD_TOKEN not configured."}

    client = _hd_client()
    try:
        created = client.create_athlete(name=name, active=True)
    except Exception as e:
        return {"status": "error", "message": f"HD creation failed: {str(e)}"}

    new_id = created.get("id") if isinstance(created, dict) else None
    if new_id:
        db.collection("athlete_info").document(athlete_uid).set({"HawkinID": str(new_id)}, merge=True)
        return {"status": "success", "message": f"Created '{name}' in HD and linked.", "hawkin_id": str(new_id)}

    return {"status": "warning", "message": f"Created '{name}' in HD but no ID returned. Re-sync to link."}


@https_fn.on_call(memory=options.MemoryOption.MB_512, timeout_sec=60, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def check_hd_connection(req: https_fn.CallableRequest) -> any:
    """Diagnostic: verify HD API connection and show what test types/data exist."""
    caller_uid, err = _require_staff(req)
    if err:
        return err

    result = {"steps": []}
    hd_token = os.environ.get("HD_TOKEN", "").strip().strip("\"'")
    result["steps"].append({"step": "HD_TOKEN", "status": "SET" if hd_token else "MISSING"})
    if not hd_token:
        return {"status": "error", "message": "HD_TOKEN not configured", "steps": result["steps"]}

    try:
        client = _hd_client()
        access = client._get_access_token()
        result["steps"].append({"step": "Access token exchange", "status": "OK", "preview": access[:20] + "..."})
    except Exception as e:
        return {"status": "error", "message": f"Token exchange failed: {e}", "steps": result["steps"]}

    try:
        types = client.get_test_types()
        result["steps"].append({
            "step": "Test types",
            "count": len(types),
            "names_and_canonical": [{"name": t.get("name"), "canonicalId": t.get("canonicalId"), "id": t.get("id")} for t in types[:20]],
        })
        cmj_id = client.find_test_type_id("CMJ")
        cmj_reb_id = client.find_test_type_id("CMJREB")
        result["steps"].append({
            "step": "Test type matching",
            "CMJ_resolved_id": cmj_id,
            "CMJ_Rebound_resolved_id": cmj_reb_id,
        })
    except Exception as e:
        return {"status": "error", "message": f"Test types fetch failed: {e}", "steps": result["steps"]}

    try:
        athletes = client.get_athletes(include_inactive=True)
        result["steps"].append({"step": "Athletes", "count": len(athletes), "sample": athletes[:3]})
    except Exception as e:
        return {"status": "error", "message": f"Athletes fetch failed: {e}", "steps": result["steps"]}

    # Try fetching CMJ tests for a wide window
    try:
        from_ts = int(datetime.datetime(2024, 1, 1).timestamp())
        to_ts = int(datetime.datetime(2027, 12, 31).timestamp())
        if cmj_id:
            cmj_tests = client.get_tests(test_type_id=cmj_id, from_ts=from_ts, to_ts=to_ts)
            result["steps"].append({
                "step": "CMJ tests with testTypeId filter",
                "count": len(cmj_tests),
                "sample_keys": list(cmj_tests[0].keys()) if cmj_tests else None,
            })
        else:
            result["steps"].append({"step": "CMJ tests", "skipped": "no test type ID resolved"})

        if cmj_reb_id:
            cmj_reb_tests = client.get_tests(test_type_id=cmj_reb_id, from_ts=from_ts, to_ts=to_ts)
            sample = cmj_reb_tests[0] if cmj_reb_tests else None
            # Surface the field names that look rebound-related so we can wire correct keys
            rebound_field_candidates = [k for k in (sample.keys() if sample else []) if "rebound" in k.lower() or "stiffness" in k.lower() or "rsi" in k.lower() or "jump_height" in k.lower()]
            result["steps"].append({
                "step": "CMJ Rebound tests with testTypeId filter",
                "count": len(cmj_reb_tests),
                "sample_keys": list(sample.keys()) if sample else None,
                "rebound_related_fields": rebound_field_candidates,
                "sample_athlete": {"id": sample.get("athlete_id"), "name": sample.get("athlete_name")} if sample else None,
            })
        else:
            result["steps"].append({"step": "CMJ Rebound tests", "skipped": "no test type ID resolved"})

        # Also try without filter, group counts by test_type_name
        all_tests = client.get_tests(from_ts=from_ts, to_ts=to_ts)
        from collections import Counter as _Counter
        type_counts = _Counter(t.get("test_type_name") for t in all_tests)
        result["steps"].append({
            "step": "All tests in window (no filter)",
            "count": len(all_tests),
            "tests_per_type": dict(sorted(type_counts.items(), key=lambda kv: -kv[1])),
        })
    except Exception as e:
        result["steps"].append({"step": "Tests fetch", "error": str(e)})

    return {"status": "success", "steps": result["steps"]}


# ──────────────────────────────────────────────
# Valor athlete list (for matching UI)
# ──────────────────────────────────────────────

@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=60, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def get_valor_athletes(req: https_fn.CallableRequest) -> any:
    """Returns the list of athletes from Valor for the matching UI."""
    if not req.auth or not req.auth.uid:
        return {"status": "error", "message": "Unauthenticated caller"}
    caller = firebase_auth.get_user(req.auth.uid)
    role = (caller.custom_claims or {}).get("role", "athlete")
    if role not in ["admin", "coach"]:
        return {"status": "error", "message": "Permission denied."}

    jwt = get_jwt_token()
    valor_url = os.environ.get("VALOR_URL", "").strip().strip("\"'")
    if not jwt or not valor_url:
        return {"status": "error", "message": "Valor credentials not configured."}

    # Build URL: handle valor_url with or without trailing slash
    endpoint = f"{valor_url.rstrip('/')}/athletes"
    response = requests.get(endpoint, headers={"Authorization": f"Bearer {jwt}"}, timeout=30)
    if response.status_code != 200:
        return {"status": "error", "message": f"Valor API returned {response.status_code}"}

    # Valor API returns {"statusCode": 200, "body": "<json string>"}
    body = response.json().get("body", "[]")
    raw = json.loads(body) if isinstance(body, str) else body
    if not isinstance(raw, list):
        return {"status": "error", "message": f"Unexpected Valor response shape: {type(raw).__name__}"}

    athletes = []
    for a in raw:
        if not isinstance(a, dict):
            continue
        fn = (a.get("FirstName") or "").strip()
        ln = (a.get("LastName") or "").strip()
        aid = str(a.get("AthleteId") or a.get("Id") or a.get("ValorID") or "")
        if fn or ln:
            athletes.append({"ValorID": aid, "Name": f"{fn} {ln}".strip()})

    # Also load which ValorIDs are already assigned in Firestore
    assigned_ids = set()
    for doc in db.collection("athlete_info").stream():
        vid = doc.to_dict().get("ValorID")
        if vid:
            assigned_ids.add(str(vid))

    for a in athletes:
        a["assigned"] = a["ValorID"] in assigned_ids

    return {"status": "success", "data": athletes}


# ──────────────────────────────────────────────
# Data entry: Testing station endpoints
# ──────────────────────────────────────────────

def _require_staff(req):
    if not req.auth or not req.auth.uid:
        return None, {"status": "error", "message": "Unauthenticated caller"}
    caller = firebase_auth.get_user(req.auth.uid)
    role = caller.custom_claims.get("role") if caller.custom_claims else "athlete"
    if role not in ["admin", "coach"]:
        return None, {"status": "error", "message": "Permission denied. Admins or Coaches only."}
    return req.auth.uid, None


@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=30, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def submit_standing_reach(req: https_fn.CallableRequest) -> any:
    caller_uid, err = _require_staff(req)
    if err:
        return err

    athlete_uid = req.data.get("athlete_uid")
    inches = req.data.get("inches")
    if not athlete_uid or inches is None:
        return {"status": "error", "message": "athlete_uid and inches are required."}

    db.collection("standing_reach").document(athlete_uid).set({
        "athlete_uid": athlete_uid,
        "StandingReachInches": float(inches),
        "recorded_by": caller_uid,
        "recorded_at": firestore.SERVER_TIMESTAMP,
    }, merge=True)

    return {"status": "success"}


@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=30, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def get_standing_reach(req: https_fn.CallableRequest) -> any:
    athlete_uid = req.data.get("athlete_uid")
    if not athlete_uid:
        return {"status": "error", "message": "athlete_uid is required."}

    doc = db.collection("standing_reach").document(athlete_uid).get()
    if doc.exists:
        return {"status": "success", "inches": doc.to_dict().get("StandingReachInches")}
    return {"status": "success", "inches": None}


@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=30, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def submit_vertical_jump(req: https_fn.CallableRequest) -> any:
    caller_uid, err = _require_staff(req)
    if err:
        return err

    athlete_uid = req.data.get("athlete_uid")
    max_touch = req.data.get("max_touch_inches")
    if not athlete_uid or max_touch is None:
        return {"status": "error", "message": "athlete_uid and max_touch_inches are required."}

    reach_doc = db.collection("standing_reach").document(athlete_uid).get()
    if not reach_doc.exists:
        return {"status": "error", "message": "Standing reach not recorded for this athlete. Enter standing reach first."}

    standing_reach = reach_doc.to_dict().get("StandingReachInches")
    if standing_reach is None:
        return {"status": "error", "message": "Standing reach value is missing."}

    vert = round(float(max_touch) - float(standing_reach), 1)

    db.collection("standing_vert").add({
        "athlete_uid": athlete_uid,
        "MaxTouchInches": float(max_touch),
        "StandingReachInches": float(standing_reach),
        "VertInches": vert,
        "recorded_by": caller_uid,
        "recorded_at": firestore.SERVER_TIMESTAMP,
    })

    return {"status": "success", "vert_inches": vert}


@https_fn.on_call(memory=options.MemoryOption.MB_256, timeout_sec=30, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def submit_broad_jump(req: https_fn.CallableRequest) -> any:
    caller_uid, err = _require_staff(req)
    if err:
        return err

    athlete_uid = req.data.get("athlete_uid")
    a1 = req.data.get("attempt1")
    a2 = req.data.get("attempt2")
    if not athlete_uid or (a1 is None and a2 is None):
        return {"status": "error", "message": "athlete_uid and at least one attempt are required."}

    vals = [v for v in [a1, a2] if v is not None]
    best = max(vals)

    db.collection("broad_jump").add({
        "athlete_uid": athlete_uid,
        "Attempt1Inches": float(a1) if a1 is not None else None,
        "Attempt2Inches": float(a2) if a2 is not None else None,
        "BestInches": float(best),
        "recorded_by": caller_uid,
        "recorded_at": firestore.SERVER_TIMESTAMP,
    })

    return {"status": "success", "best_inches": float(best)}


# ──────────────────────────────────────────────
# Bookeo sync
# ──────────────────────────────────────────────

@https_fn.on_call(memory=options.MemoryOption.GB_1, timeout_sec=300, cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
@safe_execute
def sync_bookeo_roster(req: https_fn.CallableRequest) -> any:
    """Pull athletes from Bookeo bookings, upsert into athlete_info, cross-ref HD and Valor."""
    caller_uid, err = _require_staff(req)
    if err:
        return err
    caller = firebase_auth.get_user(caller_uid)
    if (caller.custom_claims or {}).get("role") != "admin":
        return {"status": "error", "message": "Admin only."}

    from func_bookeo import get_bookings, extract_athletes, normalize_name

    product_id = os.environ.get("BOOKEO_PRODUCT_ID", "").strip().strip("\"'")
    start_time = req.data.get("start_time", "2026-05-09T01:00:00-07:00")
    end_time = req.data.get("end_time", "2026-05-09T23:00:00-07:00")

    bookings = get_bookings(product_id, start_time, end_time)
    bookeo_athletes = extract_athletes(bookings)

    # Load existing athlete_info keyed on bookeo_person_id and by normalized name
    existing_docs = list(db.collection("athlete_info").stream())
    existing_by_bookeo_id = {}
    existing_by_norm_name = {}
    for doc in existing_docs:
        d = doc.to_dict()
        d["_doc_id"] = doc.id
        bpid = d.get("bookeo_person_id")
        if bpid:
            existing_by_bookeo_id[bpid] = d
        name = d.get("Name", "")
        if name:
            existing_by_norm_name[normalize_name(name)] = d

    # Load HD roster for cross-ref
    hd_by_norm_name = {}
    try:
        if os.environ.get("HD_TOKEN", "").strip():
            for a in _hd_client().get_athletes(include_inactive=True):
                if a.get("name") and a.get("id"):
                    hd_by_norm_name[normalize_name(str(a["name"]))] = str(a["id"])
    except Exception as e:
        print(f"HD roster fetch failed during sync: {e}")

    # Load Valor roster for cross-ref
    valor_by_norm_name = {}
    try:
        jwt = get_jwt_token()
        valor_url = os.environ.get("VALOR_URL", "").strip().strip("\"'").rstrip("/")
        if jwt and valor_url:
            resp = requests.get(f"{valor_url}/athletes", headers={"Authorization": f"Bearer {jwt}"}, timeout=30)
            if resp.status_code == 200:
                body = resp.json().get("body", "[]")
                parsed = json.loads(body) if isinstance(body, str) else body
                if isinstance(parsed, list):
                    for a in parsed:
                        if not isinstance(a, dict):
                            continue
                        fn = (a.get("FirstName") or "").strip()
                        ln = (a.get("LastName") or "").strip()
                        aid = str(a.get("AthleteId") or a.get("Id") or a.get("ValorID") or "")
                        if fn or ln:
                            valor_by_norm_name[normalize_name(f"{fn} {ln}")] = aid
    except Exception as e:
        print(f"Valor roster fetch failed during sync: {e}")

    results = {"created": 0, "matched": 0, "missing_valor": [], "missing_hd": [], "errors": []}

    for athlete in bookeo_athletes:
        try:
            bpid = athlete["bookeo_person_id"]
            norm = normalize_name(athlete["Name"])

            # Determine Firestore doc to upsert
            existing = existing_by_bookeo_id.get(bpid) or existing_by_norm_name.get(norm)

            # Cross-ref HD
            hd_id = hd_by_norm_name.get(norm)
            # Cross-ref Valor
            valor_id = valor_by_norm_name.get(norm)

            sync_status = {}
            if hd_id:
                sync_status["hd"] = "present"
            else:
                sync_status["hd"] = "missing"
                results["missing_hd"].append(athlete["Name"])
            if valor_id:
                sync_status["valor"] = "present"
            else:
                sync_status["valor"] = "missing"
                results["missing_valor"].append(athlete["Name"])

            doc_data = {
                "bookeo_person_id": bpid,
                "bookeo_customer_id": athlete.get("bookeo_customer_id"),
                "Name": athlete["Name"],
                "Email": athlete.get("Email"),
                "BirthDate": athlete.get("BirthDate"),
                "Gender": athlete.get("Gender"),
                "HeightInches": athlete.get("HeightInches"),
                "CurrentSchool": athlete.get("CurrentSchool"),
                "Sports": athlete.get("Sports"),
                "Positions": athlete.get("Positions"),
                "GradYear": athlete.get("GradYear"),
                "sync_status": sync_status,
            }
            if hd_id:
                doc_data["HawkinID"] = hd_id
            if valor_id:
                doc_data["ValorID"] = valor_id

            # Remove None values so merge doesn't overwrite with null
            doc_data = {k: v for k, v in doc_data.items() if v is not None}

            if existing:
                doc_id = existing["_doc_id"]
                db.collection("athlete_info").document(doc_id).set(doc_data, merge=True)
                results["matched"] += 1
            else:
                db.collection("athlete_info").add(doc_data)
                results["created"] += 1

        except Exception as e:
            results["errors"].append(f"{athlete.get('Name', '?')}: {str(e)}")

    return {"status": "success", **results}