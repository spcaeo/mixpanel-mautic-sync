# sync.py

import os
import requests  # Added this import
from datetime import datetime, timezone
from dotenv import load_dotenv
from event_retriever import get_event_summary_text
from ai_analyzer import AIAnalyzer
from sync_helpers import (
    fetch_profiles_for_created_date,
    fetch_profiles_since_last_run,
    post_mautic_contact,
    patch_mautic_contact,
    parse_mautic_id,
    save_last_run_time,
    map_mixpanel_to_mautic,
    get_mixpanel_headers,
    get_env_var
)

load_dotenv()

def do_sync_for_profiles(profiles, update_last_run=False):
    if not profiles:
        print("[SYNC] No profiles to process.")
        return
    filtered = []
    for p in profiles:
        em = p.get("$email", "").strip().lower()
        if not em or "spaceo" in em:
            continue
        filtered.append(p)
    print(f"[SYNC] After filtering empty/spaceo: {len(filtered)} remain.")

    ai_analyzer = AIAnalyzer()

    for prof in filtered:
        distinct_id = prof["distinct_id"]
        mapped_data = map_mixpanel_to_mautic(prof)
        mapped_data["mixpanel_distinct_id"] = distinct_id

        event_summary_json = get_event_summary_text(
            distinct_id=distinct_id,
            days_back=2,
            short_summary=True,
            filter_event_names=[],
            detailed_event_names=[
                "Job Selected",
                "Create Job Save Button Clicked",
                "Job Dashboard Start Work At Clicked",
                "Job Dashboard Create Work Entry Button Clicked",
                "Job Dashboard Single Work Entry Clicked",
                "Subscription Selected",
                "Subscription Plan PURCHASED",
                "Pay Period Tab Option Clicked",
                "Pay Period Single Work Entry Clicked",
                "Work Details Entry Screen Open"
            ],
            detailed_props="custom",
            global_props="all",
            no_timestamp=True,
            exclude_props=[],
            profile_properties=mapped_data
        )
        mapped_data["mixpanel_event_summary"] = event_summary_json

        # Use AI Analyzer to generate a summary - now returns dict with subject, body, error
        ai_result = ai_analyzer.summarize_events(event_summary_json)
        
        # Set current timestamp
        current_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        # Map the AI results to the new fields
        mapped_data["mixpanel_first_email_ts"] = current_ts
        
        if ai_result["error"]:
            mapped_data["mixpanel_first_email_erro"] = ai_result["error"]
            mapped_data["mixpanel_first_email_subj"] = ""
            mapped_data["mixpanel_first_email_body"] = ""
        else:
            mapped_data["mixpanel_first_email_subj"] = ai_result["subject"]
            mapped_data["mixpanel_first_email_body"] = ai_result["body"]
            mapped_data["mixpanel_first_email_erro"] = ""

        # Remove old fields if they exist
        mapped_data.pop("mixpanel_ai_summary", None)
        mapped_data.pop("mixpanel_ai_summary_ts", None)

        mautic_id = prof.get("mautic_id")
        if not mapped_data.get("email"):
            continue

        if mautic_id:
            r_patch = patch_mautic_contact(mautic_id, mapped_data, distinct_id=distinct_id)
            if r_patch.status_code == 404:
                r_post = post_mautic_contact(mapped_data, distinct_id=distinct_id)
                if r_post.status_code in (200, 201):
                    try:
                        new_id = parse_mautic_id(r_post.json())
                    except Exception as e:
                        print(f"[ERROR] Failed to parse Mautic ID: {e}")
            elif r_patch.status_code in (200, 201):
                print(f"[SYNC] Updated Mautic ID={mautic_id}, email={mapped_data['email']}")
        else:
            r_post = post_mautic_contact(mapped_data, distinct_id=distinct_id)
            if r_post.status_code in (200, 201):
                try:
                    new_id = parse_mautic_id(r_post.json())
                except Exception as e:
                    print(f"[ERROR] Failed to parse Mautic ID: {e}")

    if update_last_run:
        new_run_time = datetime.now(timezone.utc).isoformat()
        save_last_run_time(new_run_time)
        print(f"[SYNC] Completed. last_run_time updated => {new_run_time}")

def sync_by_day(day_str):
    try:
        datetime.strptime(day_str, "%Y-%m-%d")
    except ValueError:
        print(f"[ERROR] Invalid date: {day_str}, must be YYYY-MM-DD.")
        return
    profiles = fetch_profiles_for_created_date(day_str)
    do_sync_for_profiles(profiles, update_last_run=False)

def sync_incremental():
    profiles = fetch_profiles_since_last_run()
    do_sync_for_profiles(profiles, update_last_run=True)

def sync_one_user(distinct_id):
    mp_project_id = get_env_var("MIXPANEL_PROJECT_ID")
    if not mp_project_id:
        print("[ERROR] No MIXPANEL_PROJECT_ID")
        return
    
    found_profile = None
    for w in [
        f'properties["distinct_id"] == "{distinct_id}"',
        f'properties["$distinct_id"] == "{distinct_id}"'
    ]:
        r = requests.get(
            "https://mixpanel.com/api/2.0/engage",
            headers=get_mixpanel_headers(),
            params={"project_id": mp_project_id, "where": w, "limit": 1}
        )
        if r.status_code != 200:
            print(f"[ERROR] Mixpanel Single Fetch: Error {r.status_code}")
            return
        results = r.json().get("results", [])
        if results:
            p = results[0].get("$properties", {})
            p["distinct_id"] = results[0].get("$distinct_id")
            found_profile = p
            break
    
    if not found_profile:
        print(f"[SYNC] No user found distinct_id={distinct_id}")
        return
    
    do_sync_for_profiles([found_profile], update_last_run=False)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mautic sync")
    parser.add_argument("--single", help="Distinct ID for one user")
    parser.add_argument("--day", help="YYYY-MM-DD to fetch from '$created' in Mixpanel")
    args = parser.parse_args()
    if args.single:
        sync_one_user(args.single)
    elif args.day:
        sync_by_day(args.day)
    else:
        sync_incremental()