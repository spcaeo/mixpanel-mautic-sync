# main.py
import os
from datetime import datetime
from mixpanel_daily_profile import get_profiles_for_date
from Temp3.mixpanel_events import fetch_user_events
import requests

def main():
    # Example: pick "today" or "yesterday" to pass to get_profiles_for_date
    today_str = datetime.now().strftime('%Y-%m-%d')
    profiles = get_profiles_for_date(today_str)

    # For each profile, do something (like upsert to Mautic)
    for p in profiles:
        # parse out email from p['$properties']['$email'], etc.
        email = p.get('$distinct_id')  # or something
        # 1) If you want more event data:
        # events = fetch_user_events(distinct_id, days_back=7)
        # combine them into usage metrics

        # 2) Upsert to Mautic
        upsert_mautic_contact(email, p)  # a function we define below

def upsert_mautic_contact(email, profile):
    """
    Example function that calls Mautic's REST API to create or update a contact
    """
    MAUTIC_URL = os.getenv("MAUTIC_BASE_URL")
    MAUTIC_USER = os.getenv("MAUTIC_USER")
    MAUTIC_PASS = os.getenv("MAUTIC_PASSWORD")

    # Build contact fields
    data = {
        "contact": {
            "email": email,
            "firstname": profile.get('$properties', {}).get('$name', ''),
            # etc. map more fields
        }
    }

    # Mautic endpoint
    url = f"{MAUTIC_URL}/api/contacts/new"
    resp = requests.post(url, auth=(MAUTIC_USER, MAUTIC_PASS), json=data)
    if resp.status_code != 200:
        print("Mautic upsert error:", resp.status_code, resp.text)
    else:
        print("Upserted contact for:", email)

if __name__ == "__main__":
    main()
