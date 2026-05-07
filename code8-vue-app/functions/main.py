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
    "MR": None
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

    if not athlete_uid:
        return {"status": "error", "message": "No athlete_uid provided"}
        
    collections = ["sprint40", "pro_agility", "standing_vert", "broad_jump"]
    metrics = {}
    ranks = {}
    
    for col in collections:
        docs = db.collection(col).where("athlete_uid", "==", athlete_uid).stream()
        # Convert firestore docs to dicts
        metrics[col] = [doc.to_dict() for doc in docs]

    # --- Calculate Combine Percentiles ---
    try:
        combine_pct = [d.to_dict() for d in db.collection("combine_percentiles").stream()]
        if combine_pct:
            pct_df = pd.DataFrame(combine_pct).sort_values("Percentile")
            
            # Sprint 40 (Lower time is better, so array is reversed for numpy interp)
            sprints = [float(s["Total"]) for s in metrics.get("sprint40", []) if s.get("Distance") in [40, "40"] and s.get("Total")]
            if sprints:
                ranks["sprint40"] = round(float(np.interp(min(sprints), pct_df["Sprint40"].values[::-1], pct_df["Percentile"].values[::-1])), 1)
                
            # Pro Agility
            agils = [float(a["Total"]) for a in metrics.get("pro_agility", []) if a.get("Distance") in [20, "20"] and a.get("Total")]
            if agils:
                ranks["proAgility"] = round(float(np.interp(min(agils), pct_df["ProAgility"].values[::-1], pct_df["Percentile"].values[::-1])), 1)

            # Vertical
            verts = [float(v["VerticalJump"]) for v in metrics.get("standing_vert", []) if v.get("VerticalJump")]
            if verts:
                ranks["verticalJump"] = round(float(np.interp(max(verts), pct_df["VerticalJump"].values, pct_df["Percentile"].values)), 1)

            # Broad
            broads = [float(b["BestBroadJump"]) for b in metrics.get("broad_jump", []) if b.get("BestBroadJump")]
            if broads:
                ranks["broadJump"] = round(float(np.interp(max(broads), pct_df["BroadJump"].values, pct_df["Percentile"].values)), 1)
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
                    return [r for r in rows if r.get("athlete_name") == athlete_name]
                return []

            # Countermovement Jump
            if hd_cache["CMJ"] is None:
                cmj_type_id = client.find_test_type_id("CMJ")
                hd_cache["CMJ"] = client.get_tests(test_type_id=cmj_type_id, from_ts=from_ts, to_ts=to_ts) if cmj_type_id else []

            cmj_rows = _filter_for_athlete(hd_cache["CMJ"])
            if cmj_rows:
                fp_pct = [d.to_dict() for d in db.collection("fp_percentiles").stream()]
                first = cmj_rows[0]
                if fp_pct and first.get("jump_height_m") is not None and first.get("mrsi") is not None:
                    f_df = pd.DataFrame(fp_pct).sort_values("Percentile")
                    ranks["fp_jump_height"] = round(float(np.interp(first["jump_height_m"], f_df["JumpHeight"].values, f_df["Percentile"].values)), 1)
                    ranks["fp_mrsi"] = round(float(np.interp(first["mrsi"], f_df["mRSI"].values, f_df["Percentile"].values)), 1)

                metrics["force_plate_cmj"] = [{
                    "Jump Height (in)": (r["jump_height_m"] * 39.3701) if r.get("jump_height_m") is not None else None,
                    "mRSI": r.get("mrsi"),
                    "Peak Rel Prop Power (W/kg)": r.get("peak_relative_propulsive_power_w_kg"),
                    "Braking Asymmetry": round(r["lr_braking_impulse_index"]) if r.get("lr_braking_impulse_index") is not None else None,
                } for r in cmj_rows]

            # Multi-Rebound
            if hd_cache["MR"] is None:
                mr_type_id = client.find_test_type_id("MR")
                hd_cache["MR"] = client.get_tests(test_type_id=mr_type_id, from_ts=from_ts, to_ts=to_ts) if mr_type_id else []

            mr_rows = _filter_for_athlete(hd_cache["MR"])
            if mr_rows:
                metrics["force_plate_mr"] = [{
                    "Number of Jumps": r.get("number_of_jumps_count"),
                    "Avg Jump Height (in)": (r["avg_jump_height_m"] * 39.3701) if r.get("avg_jump_height_m") is not None else None,
                    "Peak Jump Height (in)": (r["peak_jump_height_m"] * 39.3701) if r.get("peak_jump_height_m") is not None else None,
                    "Avg RSI": r.get("avg_rsi"),
                    "Peak RSI": r.get("peak_rsi"),
                } for r in mr_rows]
    except Exception as e:
        print(f"Error fetching HD metrics: {e}")
        
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
def register_athlete(req: https_fn.CallableRequest) -> any:
    """Public endpoint for athletes to self-register. Validates against athlete_info."""
    email = req.data.get("email", "").strip()
    password = req.data.get("password")
    
    if not email or not password:
        return {"status": "error", "message": "Email and password are required."}
        
    # Stream all athletes and find a case-insensitive match for the email
    email_lower = email.lower()
    docs = db.collection("athlete_info").stream()
    athlete_doc = None
    doc_id = None
    for doc in docs:
        d = doc.to_dict()
        doc_email = d.get("email") or d.get("Email")
        if doc_email and str(doc_email).strip().lower() == email_lower:
            athlete_doc = d
            doc_id = doc.id
            break
            
    if not athlete_doc:
        return {"status": "error", "message": "Email not found in the roster. Please ensure your email matches the one provided to your coach."}
        
    athlete_name = athlete_doc.get("Name")
    
    try:
        user = firebase_auth.create_user(email=email, password=password)
        firebase_auth.set_custom_user_claims(user.uid, {"role": "athlete", "athlete_name": athlete_name})
        
        # Update athlete_info with additional details from sign up
        update_data = {}
        for key in ["BirthDate", "BirthYear", "BirthMonth", "Gender", "GradYear", "SchoolGrade", "HeightInches", "LimbDominance", "Sports", "Positions", "CurrentSchool"]:
            if key in req.data and req.data[key]:
                update_data[key] = req.data[key]
        
        if update_data and doc_id:
            db.collection("athlete_info").document(doc_id).update(update_data)
            
        return {"status": "success", "message": "Successfully registered."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
            
    if not uid:
        doc_ref = db.collection("athlete_info").document()
        uid = doc_ref.id
        update_data["athlete_uid"] = uid
        doc_ref.set(update_data)
    else:
        db.collection("athlete_info").document(uid).set(update_data, merge=True)
        
    return {"status": "success", "message": "Successfully updated athlete info.", "athlete_uid": uid}


# ──────────────────────────────────────────────
# Backfill: sync historic Swift IDs onto athlete_info
# ──────────────────────────────────────────────

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
        mr_id = client.find_test_type_id("MR")
        result["steps"].append({
            "step": "Test type matching",
            "CMJ_resolved_id": cmj_id,
            "MR_resolved_id": mr_id,
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
                "sample": cmj_tests[0] if cmj_tests else None,
            })
        else:
            result["steps"].append({"step": "CMJ tests", "skipped": "no test type ID resolved"})

        # Also try without filter
        all_tests = client.get_tests(from_ts=from_ts, to_ts=to_ts)
        unique_test_types = list({t.get("test_type_name") for t in all_tests})
        result["steps"].append({
            "step": "All tests in window (no filter)",
            "count": len(all_tests),
            "unique_test_type_names": unique_test_types,
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