import pandas as pd
from firebase_admin import initialize_app, firestore, credentials

# NOTE: You will need to download your service account key from 
# Firebase Console > Project Settings > Service Accounts > Generate new private key
cred = credentials.Certificate(r"C:\src\code8\slo-combine\code8-vue-app\service-account.json")
initialize_app(cred)
db = firestore.client()

def upload_base_athletes(csv_path, collection_name):
    df = pd.read_csv(csv_path)
    df = df.where(pd.notnull(df), None) # Handle NaN values
    records = df.to_dict(orient='records')
    
    mapping = {}
    batch = db.batch()
    collection_ref = db.collection(collection_name)
    
    for i, record in enumerate(records):
        doc_ref = collection_ref.document() # Auto-generate ID
        batch.set(doc_ref, record)
        
        # Map the generated ID to the athlete's name
        if 'Name' in record and record['Name']:
            mapping[record['Name']] = doc_ref.id
        
        # Batch write limits to 500 ops
        if (i + 1) % 500 == 0:
            batch.commit()
            batch = db.batch()
            
    batch.commit()
    print(f"Successfully uploaded {len(records)} records to {collection_name}")
    return mapping

def upload_csv_to_firestore(csv_path, collection_name, athlete_mapping=None):
    df = pd.read_csv(csv_path)
    df = df.where(pd.notnull(df), None) # Handle NaN values
    records = df.to_dict(orient='records')
    
    batch = db.batch()
    collection_ref = db.collection(collection_name)
    
    for i, record in enumerate(records):
        # Inject the athlete_uid if mapping is provided and Name exists
        if athlete_mapping and 'Name' in record and record['Name'] in athlete_mapping:
            record['athlete_uid'] = athlete_mapping[record['Name']]
            
        doc_ref = collection_ref.document() # Auto-generate ID
        batch.set(doc_ref, record)
        
        # Batch write limits to 500 ops
        if (i + 1) % 500 == 0:
            batch.commit()
            batch = db.batch()
            
    batch.commit()
    print(f"Successfully uploaded {len(records)} records to {collection_name}")

# 1. Upload the base profile/info first to get the generated UUIDs
print("Uploading athlete info and generating mapping...")
mapping = upload_base_athletes(r"C:\src\code8\slo-combine\data\athelte_info.csv", 'athlete_info')

# 2. Upload the rest of the sheets, passing in the mapping so the UUID gets injected
print("Uploading performance data with mapped UUIDs...")
upload_csv_to_firestore(r"C:\src\code8\slo-combine\data\sprint40.csv", 'sprint40', mapping)
upload_csv_to_firestore(r"C:\src\code8\slo-combine\data\pro-agility.csv", 'pro_agility', mapping)
upload_csv_to_firestore(r"C:\src\code8\slo-combine\data\Standing_Broad_Jump_Test.csv", 'broad_jump', mapping)
upload_csv_to_firestore(r"C:\src\code8\slo-combine\data\swift_slo25.csv", 'swift_slo25', mapping)
upload_csv_to_firestore(r"C:\src\code8\slo-combine\data\Vertical_Jump_Test.csv", 'standing_vert', mapping)
upload_csv_to_firestore(r"C:\src\code8\slo-combine\data\SLO CC Athlete Profiles.csv", 'slo_cc_athlete_profiles', mapping)
