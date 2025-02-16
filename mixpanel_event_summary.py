# mixpanel_event_summary.py
def function(distinct_id):
    import os
    import requests
    import base64
    import json
    import time
    from datetime import datetime, timedelta

    os.environ["MIXPANEL_PROJECT_ID"] = "2342291"
    os.environ["MIXPANEL_API_TOKEN"] = "5c4eed1b754439f60fd94836c8774437"
    os.environ["MIXPANEL_API_SECRET"] = "1a47ceeacaa9fea8f878d2e3e2910762"

    def get_mixpanel_headers():
        api_secret = os.getenv("MIXPANEL_API_SECRET")
        creds = base64.b64encode(f"{api_secret}:".encode()).decode()
        return {"Authorization": f"Basic {creds}", "Accept": "application/json"}

    def convert_date(value):
        try:
            dt = datetime.fromisoformat(value.replace("T", " ").split("+")[0])
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return value

    def try_convert_number(value):
        try:
            return float(value)
        except Exception:
            return value

    def convert_country(code):
        mapping = {"IN": "India", "US": "United States", "GB": "United Kingdom", "CA": "Canada"}
        return mapping.get(code, code)

    FIELD_MAPPING = {
        "$email": "email",
        "$first_name": "firstname",
        "$last_name": "lastname",
        "$city": "city",
        "$region": "state",
        "$country_code": "country",
        "$timezone": "timezone",
        "$name": "full_name",
        "deviceName": "device_name",
        "App Version": "app_version",
        "Membership": "membership",
        "Subscription Cost": "subscription_cost",
        "Subscription Name": "subscription_name",
        "Subscription Status": "subscription_status",
        "Total Entries": "total_entries",
        "app_user_id": "app_user_id",
        "currency": "currency",
        "job_count": "job_count",
        "last_used": "last_used",
        "platform": "platform",
        "subscription_expire_date": "subscription_expire_date",
        "subscription_original_purchase_date": "subscription_original_purchase_date",
        "subscription_plan": "subscription_plan",
        "subscription_purchased_date": "subscription_purchased_date",
        "total_earns": "total_earns",
        "total_hours": "total_hours",
        "userSubscribed": "user_subscribed",
        "$last_seen": "lastActive",
        "distinct_id": "mixpanel_distinct_id"
    }

    def fetch_profile(distinct_id):
        base_url = "https://mixpanel.com/api/2.0/engage"
        headers = get_mixpanel_headers()
        queries = [
            f'properties["distinct_id"] == "{distinct_id}"',
            f'properties["$distinct_id"] == "{distinct_id}"'
        ]
        for query in queries:
            params = {"project_id": os.getenv("MIXPANEL_PROJECT_ID"), "where": query, "limit": 1}
            try:
                response = requests.get(base_url, headers=headers, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if results:
                        profile = results[0].get("$properties", {})
                        if "distinct_id" not in profile:
                            profile["distinct_id"] = results[0].get("$distinct_id")
                        return profile
            except Exception:
                continue
        return None

    def fetch_events(query_id, from_date, to_date):
        export_url = "https://data.mixpanel.com/api/2.0/export"
        headers = get_mixpanel_headers()
        queries = [
            f'properties["distinct_id"] == "{query_id}"',
            f'properties["$distinct_id"] == "{query_id}"'
        ]
        events = []
        for query in queries:
            params = {"where": query, "from_date": from_date, "to_date": to_date}
            try:
                response = requests.get(export_url, headers=headers, params=params, stream=True, timeout=120)
                if response.status_code != 200:
                    continue
                events_data = []
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        event_obj = json.loads(line)
                        events_data.append(event_obj)
                    except json.JSONDecodeError:
                        continue
                if events_data:
                    for event in events_data:
                        props = event.get("properties", {})
                        event_name = event.get("event")
                        timestamp = props.get("time")
                        events.append({"event_name": event_name, "timestamp": timestamp, "all_event_properties": props})
                    break
            except Exception:
                continue
        return events

    now = datetime.now()
    one_year_ago = now - timedelta(days=365)
    to_dt = now - timedelta(days=1)
    from_date = one_year_ago.strftime("%Y-%m-%d")
    to_date = to_dt.strftime("%Y-%m-%d")

    raw_profile = fetch_profile(distinct_id)
    if raw_profile is None:
        return json.dumps({"profile_properties": {}, "user_events": []}, indent=2)

    query_id = raw_profile.get("distinct_id") or distinct_id

    transformed_profile = {}
    for raw_key, raw_value in raw_profile.items():
        if raw_key in FIELD_MAPPING:
            new_key = FIELD_MAPPING[raw_key]
            if new_key in ["subscription_expire_date", "subscription_original_purchase_date", "subscription_purchased_date", "$created", "$last_seen"]:
                new_value = convert_date(raw_value)
            else:
                new_value = raw_value
            if new_key in ["total_entries", "job_count", "total_earns", "total_hours"]:
                new_value = try_convert_number(new_value)
            if new_key == "country":
                new_value = convert_country(new_value)
            transformed_profile[new_key] = new_value

    if "ipAddress" not in transformed_profile:
        transformed_profile["ipAddress"] = "127.0.0.1"
    if "lastActive" not in transformed_profile and "$last_seen" not in raw_profile:
        transformed_profile["lastActive"] = convert_date(datetime.now().isoformat())
    transformed_profile["overwriteWithBlank"] = ""
    transformed_profile["owner"] = "1"

    events = fetch_events(query_id, from_date, to_date)

    output_obj = {"profile_properties": transformed_profile, "user_events": events}
    mixpanel_event_summery = json.dumps(output_obj, indent=2)
    return mixpanel_event_summery
