import pandas as pd
from firebase_admin import initialize_app, firestore, credentials

# 1. Initialize Firebase Admin
cred = credentials.Certificate(r"C:\src\code8\slo-combine\code8-vue-app\service-account.json")
initialize_app(cred)
db = firestore.client()

def upload_percentiles(csv_path, collection_name):
    print(f"Uploading {collection_name}...")
    df = pd.read_csv(csv_path)
    df = df.where(pd.notnull(df), None) 
    records = df.to_dict(orient='records')
    
    batch = db.batch()
    collection_ref = db.collection(collection_name)
    
    for i, record in enumerate(records):
        doc_ref = collection_ref.document(str(record.get('Percentile', i)))
        batch.set(doc_ref, record)
        if (i + 1) % 400 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()

upload_percentiles(r"C:\src\code8\slo-combine\data\combinePercentiles.csv", 'combine_percentiles')
upload_percentiles(r"C:\src\code8\slo-combine\data\ForcePlatesPercentiles.csv", 'fp_percentiles')
upload_percentiles(r"C:\src\code8\slo-combine\data\nflCombineforceplatePercentiles.csv", 'nfl_fp_percentiles')
print("Percentiles seeded successfully!")