"""
One-off athlete deduplication script.

Run AFTER sync_bookeo_roster has populated bookeo_person_id on canonical records.
Uses the Firebase Admin SDK via the local service account.

Usage:
    python dedup_athletes.py --dry-run   # preview only
    python dedup_athletes.py             # apply changes
"""
import re
import sys
from collections import defaultdict
from firebase_admin import initialize_app, firestore, credentials

cred = credentials.Certificate(r"code8-vue-app\service-account.json")
initialize_app(cred)
db = firestore.client()

DRY_RUN = "--dry-run" in sys.argv

LINKED_COLLECTIONS = [
    "athlete_summaries",
    "standing_reach",
    "standing_vert",
    "broad_jump",
    "sprint40",
    "pro_agility",
]


def normalize(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[.\-']", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def pick_winner(docs: list[dict]) -> dict:
    with_bookeo = [d for d in docs if d.get("bookeo_person_id")]
    if with_bookeo:
        return with_bookeo[0]
    return sorted(docs, key=lambda d: d["_doc_id"])[0]


def merge_keys(winner: dict, losers: list[dict]) -> dict:
    merge_fields = ["HawkinID", "ValorID", "SprintID", "ProAgilID", "bookeo_person_id", "bookeo_customer_id"]
    updates = {}
    for field in merge_fields:
        if not winner.get(field):
            for loser in losers:
                if loser.get(field):
                    updates[field] = loser[field]
                    break
    return updates


def repoint_linked_docs(winner_uid: str, loser_uids: list[str]):
    for collection in LINKED_COLLECTIONS:
        for loser_uid in loser_uids:
            if collection == "standing_reach":
                doc = db.collection(collection).document(loser_uid).get()
                if doc.exists:
                    data = doc.to_dict()
                    data["athlete_uid"] = winner_uid
                    if not DRY_RUN:
                        db.collection(collection).document(winner_uid).set(data, merge=True)
                        db.collection(collection).document(loser_uid).delete()
                    print(f"  {collection}/{loser_uid} -> {winner_uid}")
            else:
                query = db.collection(collection).where("athlete_uid", "==", loser_uid).stream()
                for doc in query:
                    if not DRY_RUN:
                        db.collection(collection).document(doc.id).update({"athlete_uid": winner_uid})
                    print(f"  {collection}/{doc.id} athlete_uid -> {winner_uid}")


def main():
    print("Loading athlete_info...")
    docs = list(db.collection("athlete_info").stream())
    athletes = []
    for doc in docs:
        d = doc.to_dict()
        d["_doc_id"] = doc.id
        athletes.append(d)

    print(f"Found {len(athletes)} athlete_info docs.")

    groups = defaultdict(list)
    for a in athletes:
        name = a.get("Name", "")
        if name:
            groups[normalize(name)].append(a)

    dupes = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"Found {len(dupes)} duplicate groups.\n")

    if not dupes:
        print("No duplicates found.")
        return

    for norm_name, group in dupes.items():
        winner = pick_winner(group)
        losers = [d for d in group if d["_doc_id"] != winner["_doc_id"]]

        print(f"Group: {norm_name}")
        print(f"  Winner: {winner['_doc_id']} ({winner.get('Name')}) bookeo={winner.get('bookeo_person_id', '-')}")
        for l in losers:
            print(f"  Loser:  {l['_doc_id']} ({l.get('Name')}) bookeo={l.get('bookeo_person_id', '-')}")

        updates = merge_keys(winner, losers)
        if updates:
            print(f"  Merging fields: {updates}")
            if not DRY_RUN:
                db.collection("athlete_info").document(winner["_doc_id"]).update(updates)

        loser_uids = [l["_doc_id"] for l in losers]
        repoint_linked_docs(winner["_doc_id"], loser_uids)

        for l in losers:
            print(f"  Deleting loser doc: {l['_doc_id']}")
            if not DRY_RUN:
                db.collection("athlete_info").document(l["_doc_id"]).delete()

        print()

    if DRY_RUN:
        print("=== DRY RUN — no changes applied ===")
    else:
        print("=== Dedup complete ===")


if __name__ == "__main__":
    main()
