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

# We need to import Hawkin Dynamics package
try:
    from hdforce import AuthManager, GetAthletes, GetTests
except ImportError:
    print("hdforce not installed yet")

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

# Locally inject the service account for full access to the new database
# We wrap this in a check to prevent "ValueError: The default Firebase app already exists."
# which notoriously crashes the local emulator during hot-reloads and causes silent "internal" errors!
if not firebase_admin._apps:
    cred_path = os.path.join(os.path.dirname(__file__), "..", "service-account.json")
    if os.path.exists(cred_path):
        # Force the Admin SDK to use the local Auth Emulator so it syncs with the Vue frontend
        # os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = "127.0.0.1:9099"
        
        from firebase_admin import credentials
        initialize_app(credentials.Certificate(cred_path))
    else:
        initialize_app() # Fallback for when deployed to production

db = firestore.client()

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
        print(f"Valor Auth failed: {response.text}")
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
        hd_token = os.environ.get("HD_TOKEN", "").strip().strip("\"'")
        if hd_token:
            AuthManager(authMethod="manual", refreshToken=hd_token)
            hd_df = GetAthletes()
            if not hd_df.empty and "id" in hd_df.columns:
                for _, row in hd_df.iterrows():
                    hd_by_id[str(row["id"])] = row.get("name", "")
    except Exception as e:
        print(f"Error fetching HD roster: {e}")

    # 3. Fetch Valor athletes (for name display / validation of links)
    valor_by_id = {}
    try:
        token = get_jwt_token()
        if token:
            valor_endpoint = os.environ.get("VALOR_URL", "").strip().strip("\"'")
            response = requests.get(f"{valor_endpoint}athletes", headers={"Authorization": f"Bearer {token}"})
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
        hd_token = os.environ.get("HD_TOKEN", "").strip().strip("\"'")
        if hd_token and (athlete_hawkin_id or athlete_name):
            AuthManager(authMethod="manual", refreshToken=hd_token)

            global hd_cache

            if hd_cache["CMJ"] is None:
                hd_cache["CMJ"] = GetTests(typeId="CMJ", from_="2025-07-23", to_="2025-07-27")

            cmj_data = hd_cache["CMJ"]
            if not cmj_data.empty:
                cmj_athlete = pd.DataFrame()
                if athlete_hawkin_id and "athlete_id" in cmj_data.columns:
                    cmj_athlete = cmj_data[cmj_data["athlete_id"].astype(str) == str(athlete_hawkin_id)]
                if cmj_athlete.empty and athlete_name and "athlete_name" in cmj_data.columns:
                    cmj_athlete = cmj_data[cmj_data["athlete_name"] == athlete_name]
                if not cmj_athlete.empty:
                    # Calculate FP Percentiles (Elite Rank)
                    fp_pct = [d.to_dict() for d in db.collection("fp_percentiles").stream()]
                    if fp_pct:
                        f_df = pd.DataFrame(fp_pct).sort_values("Percentile")
                        ranks["fp_jump_height"] = round(float(np.interp(cmj_athlete["jump_height_m"].values[0], f_df["JumpHeight"].values, f_df["Percentile"].values)), 1)
                        ranks["fp_mrsi"] = round(float(np.interp(cmj_athlete["mrsi"].values[0], f_df["mRSI"].values, f_df["Percentile"].values)), 1)

                    cmj_df = pd.DataFrame({
                        "Jump Height (in)": cmj_athlete["jump_height_m"] * 39.3701,
                        "mRSI": cmj_athlete["mrsi"],
                        "Peak Rel Prop Power (W/kg)": cmj_athlete["peak_relative_propulsive_power_w_kg"],
                        "Braking Asymmetry": cmj_athlete["lr_braking_impulse_index"].round(0)
                    })
                    cmj_df = cmj_df.where(pd.notnull(cmj_df), None)
                    metrics["force_plate_cmj"] = cmj_df.to_dict(orient="records")

            if hd_cache["MR"] is None:
                hd_cache["MR"] = GetTests(typeId="MR", from_="2025-07-23", to_="2025-07-27")

            mr_data = hd_cache["MR"]
            if not mr_data.empty:
                mr_athlete = pd.DataFrame()
                if athlete_hawkin_id and "athlete_id" in mr_data.columns:
                    mr_athlete = mr_data[mr_data["athlete_id"].astype(str) == str(athlete_hawkin_id)]
                if mr_athlete.empty and athlete_name and "athlete_name" in mr_data.columns:
                    mr_athlete = mr_data[mr_data["athlete_name"] == athlete_name]
                if not mr_athlete.empty:
                    mr_df = pd.DataFrame({
                        "Number of Jumps": mr_athlete["number_of_jumps_count"],
                        "Avg Jump Height (in)": mr_athlete["avg_jump_height_m"] * 39.3701,
                        "Peak Jump Height (in)": mr_athlete["peak_jump_height_m"] * 39.3701,
                        "Avg RSI": mr_athlete["avg_rsi"],
                        "Peak RSI": mr_athlete["peak_rsi"]
                    })
                    mr_df = mr_df.where(pd.notnull(mr_df), None)
                    metrics["force_plate_mr"] = mr_df.to_dict(orient="records")
    except Exception as e:
        print(f"Error fetching HD metrics: {e}")
        
    # Fetch Valor Movement Data
    metrics["valor"] = {"Shoulder": 0, "Ankle": 0, "Hip": 0}
    try:
        if athlete_valor_id:
            token = get_jwt_token()
            if token:
                valor_endpoint = os.environ.get("VALOR_URL", "").strip().strip("\"'")
                headers = {"Authorization": f"Bearer {token}"}
                
                global valor_cache
                if valor_cache["sessions"] is None:
                    # Fetch sessions and cache them globally to maintain speed
                    all_items = []
                    continuation_token = '""'
                    for _ in range(3): # Limit to 3 pages to prevent hangs
                        req_headers = {**headers, 'X-Continuation-Token': continuation_token}
                        res = requests.get(f"{valor_endpoint}sessions", headers=req_headers)
                        if res.status_code == 200:
                            jdata = res.json()
                            body = jdata.get("body", "[]")
                            all_items.extend(json.loads(body) if isinstance(body, str) else body)
                            continuation_token = jdata.get("X-Continuation-Token")
                            if not continuation_token or continuation_token == "null":
                                break
                        else:
                            break
                    df_sess = pd.DataFrame(all_items)
                    if not df_sess.empty and 'Date' in df_sess.columns:
                        df_sess = df_sess[df_sess['Date'].str.startswith("2025-07-26")]
                    valor_cache["sessions"] = df_sess
                
                sess_df = valor_cache["sessions"]
                if sess_df is not None and not sess_df.empty:
                    athlete_sessions = sess_df[sess_df['Athlete ID'].astype(str) == str(athlete_valor_id)]
                    
                    def get_score(session_names):
                        keys = athlete_sessions[athlete_sessions['Session Name'].isin(session_names)]['s3Key'].tolist()
                        scores = []
                        for k in keys:
                            res = requests.get(f"{valor_endpoint}reportData", headers=headers, params={"s3Key": k})
                            if res.status_code == 200:
                                jdata = res.json()
                                body = jdata.get("body", "{}")
                                # The API returns the body as a stringified JSON, so we must parse it
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
    for key in ["Name", "Email", "BirthDate", "Gender", "GradYear", "SchoolGrade", "HeightInches", "LimbDominance", "Sports", "Positions", "CurrentSchool", "ValorID", "HawkinID"]:
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

    response = requests.get(f"{valor_url}/athletes", headers={"Authorization": f"Bearer {jwt}"}, timeout=30)
    if response.status_code != 200:
        return {"status": "error", "message": f"Valor API returned {response.status_code}"}

    raw = response.json()
    athletes = []
    for a in raw:
        fn = (a.get("FirstName") or "").strip()
        ln = (a.get("LastName") or "").strip()
        aid = str(a.get("AthleteId") or a.get("Id") or "")
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
        hd_token = os.environ.get("HD_TOKEN", "").strip().strip("\"'")
        if hd_token:
            AuthManager(authMethod="manual", refreshToken=hd_token)
            hd_df = GetAthletes()
            if not hd_df.empty and "name" in hd_df.columns:
                for _, row in hd_df.iterrows():
                    hd_by_norm_name[normalize_name(str(row["name"]))] = str(row["id"])
    except Exception as e:
        print(f"HD roster fetch failed during sync: {e}")

    # Load Valor roster for cross-ref
    valor_by_norm_name = {}
    try:
        jwt = get_jwt_token()
        valor_url = os.environ.get("VALOR_URL", "").strip().strip("\"'")
        if jwt and valor_url:
            resp = requests.get(f"{valor_url}/athletes", headers={"Authorization": f"Bearer {jwt}"}, timeout=30)
            if resp.status_code == 200:
                for a in resp.json():
                    fn = (a.get("FirstName") or "").strip()
                    ln = (a.get("LastName") or "").strip()
                    aid = str(a.get("AthleteId") or a.get("Id") or "")
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