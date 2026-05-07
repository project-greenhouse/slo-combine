import pandas as pd
from firebase_admin import initialize_app, firestore, credentials
from dateutil import parser

# 1. Initialize Firebase Admin
cred = credentials.Certificate(r"C:\src\code8\slo-combine\code8-vue-app\service-account.json")
initialize_app(cred)
db = firestore.client()

# 2. Fetch current Athlete Mapping so we can inject the correct athlete_uid
print("Fetching active athlete mapping from Firestore...")
docs = db.collection('athlete_info').stream()
mapping = {}
for doc in docs:
    data = doc.to_dict()
    if 'Name' in data:
        mapping[data['Name']] = doc.id

# 3. Read the extracted CSV
print("Reading legacy summaries CSV...")
csv_path = r"C:\src\code8\slo-combine\data\athlete_summaries.csv"
df = pd.read_csv(csv_path)
df = df.where(pd.notnull(df), None) # Handle NaN values cleanly

# 4. Batch Upload to Firestore
batch = db.batch()
collection_ref = db.collection('athlete_summaries')
count = 0

for _, row in df.iterrows():
    athlete_name = row.get('athlete_name')
    summary_html = row.get('summary_html')
    
    if not athlete_name or not summary_html:
        continue
        
    record = {
        "athlete_name": athlete_name,
        "athlete_uid": mapping.get(athlete_name), # Link to the new Firestore UUID!
        "author": "Supabase Legacy",
        "summary_html": summary_html,
        "created_at": parser.parse(str(row['created_at'])) if row.get('created_at') else firestore.SERVER_TIMESTAMP
    }
    
    doc_ref = collection_ref.document()
    batch.set(doc_ref, record)
    count += 1
    
    # Commit in batches of 500 (Firestore limit)
    if count % 500 == 0:
        batch.commit()
        batch = db.batch()

batch.commit()
print(f"Successfully uploaded {count} historical summary records to Firestore!")