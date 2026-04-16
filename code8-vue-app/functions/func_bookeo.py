import os
import requests

BOOKEO_BASE = "https://api.bookeo.com/v2"


def _params():
    return {
        "apiKey": os.environ.get("BOOKEO_API_KEY", "").strip().strip("\"'"),
        "secretKey": os.environ.get("BOOKEO_SECRET", "").strip().strip("\"'"),
    }


def get_bookings(product_id: str, start_time: str, end_time: str) -> list[dict]:
    """Fetch all bookings for a product within a time window, with pagination."""
    params = {
        **_params(),
        "productId": product_id,
        "startTime": start_time,
        "endTime": end_time,
        "expandCustomer": "true",
        "expandParticipants": "true",
        "itemsPerPage": 50,
    }

    all_bookings = []
    page_token = None

    while True:
        if page_token:
            params["pageNavigationToken"] = page_token
        resp = requests.get(f"{BOOKEO_BASE}/bookings", params=params, timeout=30)
        resp.raise_for_status()
        body = resp.json()

        all_bookings.extend(body.get("data", []))

        info = body.get("info", {})
        if info.get("currentPage", 1) >= info.get("totalPages", 1):
            break
        page_token = info.get("pageNavigationToken")
        if not page_token:
            break

    return all_bookings


CUSTOM_FIELD_MAP = {
    "Year in School": "GradYear",
    "Height (inches)": "HeightInches",
    "Weight (lbs)": "WeightLbs",
    "School/Club Team": "CurrentSchool",
    "Primary Sport": "Sports",
    "Primary Position": "Positions",
    "T-Shirt Size": "TShirtSize",
    "Emergency Contact": "EmergencyContact",
}


def extract_athletes(bookings: list[dict]) -> list[dict]:
    """Extract normalized athlete records from Bookeo bookings."""
    athletes = []
    seen_ids = set()

    for booking in bookings:
        if booking.get("canceled"):
            continue

        participants = booking.get("participants", {}).get("details", [])
        customer = booking.get("customer", {})
        customer_id = booking.get("customerId")

        for p in participants:
            person = p.get("personDetails", {})
            person_id = person.get("id")
            if not person_id or person_id in seen_ids:
                continue
            seen_ids.add(person_id)

            custom = {}
            for cf in person.get("customFields", []):
                mapped = CUSTOM_FIELD_MAP.get(cf.get("name"))
                if mapped:
                    custom[mapped] = cf.get("value")

            first = (person.get("firstName") or "").strip()
            last = (person.get("lastName") or "").strip()

            athletes.append({
                "bookeo_person_id": person_id,
                "bookeo_customer_id": customer_id,
                "Name": f"{first} {last}",
                "FirstName": first,
                "LastName": last,
                "Email": person.get("emailAddress") or customer.get("emailAddress"),
                "BirthDate": person.get("dateOfBirth"),
                "Gender": person.get("gender"),
                "Phone": next((ph.get("number") for ph in customer.get("phoneNumbers", [])), None),
                **custom,
            })

    return athletes


def normalize_name(name: str) -> str:
    """Normalize an athlete name for fuzzy matching."""
    import re
    name = name.lower().strip()
    name = re.sub(r"[.\-']", "", name)
    name = re.sub(r"\s+", " ", name)
    return name
