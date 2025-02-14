# event_retriever.py
import os
import requests
import base64
import json
import traceback
from datetime import datetime, timedelta

class MixpanelDataRetriever:
    def __init__(self, config):
        """
        Initialize with a config (dict or JSON string) containing required settings.
        Expected structure:
        {
          "required_settings": {
            "MIXPANEL_PROJECT_ID": "...",
            "MIXPANEL_API_TOKEN": "...",
            "MIXPANEL_API_SECRET": "..."
          }
        }
        """
        self.config = config if isinstance(config, dict) else json.loads(config)
        req = self.config.get("required_settings", {})
        self.project_id = req.get("MIXPANEL_PROJECT_ID")
        self.api_token = req.get("MIXPANEL_API_TOKEN")
        self.api_secret = req.get("MIXPANEL_API_SECRET")
        # Base endpoints
        self.base_url = "https://mixpanel.com/api/2.0"
        self.export_base_url = "https://data.mixpanel.com/api/2.0/export"

    def get_user_events(
        self,
        distinct_id,
        profile_properties=None,
        days_back=365,
        filter_event_names=None,
        start_date=None,
        end_date=None,
        limit_events=None,
        short_summary=False,
        detailed_event_names=None,
        detailed_props="all",
        global_props="all",
        no_timestamp=False,
        exclude_props=None,
    ):
        try:
            # Prepare headers using API secret for Basic Auth
            auth_str = f"{self.api_secret}:".encode()
            headers = {
                "Authorization": f"Basic {base64.b64encode(auth_str).decode()}",
                "Accept": "application/json",
            }

            # Determine date range using local time.
            # If start_date/end_date are not provided, use days_back.
            # To match Mixpanel's "today" (which appears to be one day behind our system date),
            # we force to_date to be (system's today - 1 day).
            if not start_date or not end_date:
                now_dt = datetime.now()  # local time
                start_dt = now_dt - timedelta(days=days_back)
                from_date = start_dt.strftime("%Y-%m-%d")
                # Force to_date to be yesterday's date (local) to avoid Mixpanel error.
                to_date = (now_dt.date() - timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                from_date = start_date
                to_date = end_date
                today_str = datetime.now().date().strftime("%Y-%m-%d")
                if to_date > today_str:
                    print(f"Warning: to_date {to_date} is later than today ({today_str}); adjusting to today's date.")
                    to_date = today_str

            # Build query strategies exactly as in your original code
            query_strategies = [
                {
                    "api_key": self.api_token,
                    "where": f'properties["distinct_id"] == "{distinct_id}"',
                    "from_date": from_date,
                    "to_date": to_date,
                },
                {
                    "api_key": self.api_token,
                    "where": f'properties["$distinct_id"] == "{distinct_id}"',
                    "from_date": from_date,
                    "to_date": to_date,
                },
            ]
            # Add a strategy based on email if available in profile_properties
            user_email = profile_properties.get("email") if profile_properties else None
            if user_email:
                query_strategies.append({
                    "api_key": self.api_token,
                    "where": f'properties["email"] == "{user_email}"',
                    "from_date": from_date,
                    "to_date": to_date,
                })

            all_events = []
            # Try each strategy until one returns events
            for strategy in query_strategies:
                response = requests.get(
                    self.export_base_url,
                    params=strategy,
                    headers=headers,
                    stream=True,
                    timeout=120,
                )
                if response.status_code != 200:
                    print(f"Strategy failed with status {response.status_code}: {response.text[:300]}")
                    continue

                events_data = []
                line_count = 0
                # Read NDJSON lines as in the original implementation
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    line_count += 1
                    try:
                        event_obj = json.loads(line)
                        events_data.append(event_obj)
                    except json.JSONDecodeError as e:
                        print(f"Skipping line due to JSON error: {e}")
                        continue

                if events_data:
                    for event in events_data:
                        props = event.get("properties", {})
                        event_name = event.get("event")
                        timestamp = props.get("time")
                        normalized_event = {
                            "event_name": event_name,
                            "timestamp": timestamp,
                            "all_event_properties": props,
                        }
                        all_events.append(normalized_event)
                    # Stop after the first successful strategy
                    break

            if not all_events:
                return None

            # Convert each event's timestamp to datetime for local filtering
            for ev in all_events:
                ts = ev.get("timestamp")
                if ts:
                    ev["_dt"] = datetime.utcfromtimestamp(int(ts))

            # Apply local date filtering if start_date and end_date are provided
            if start_date and end_date:
                start_dt_local = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt_local = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                all_events = [ev for ev in all_events if ev.get("_dt") and start_dt_local <= ev["_dt"] < end_dt_local]

            # Filter events by event names if provided
            if filter_event_names and isinstance(filter_event_names, list):
                all_events = [ev for ev in all_events if ev.get("event_name") in filter_event_names]

            # Sort events descending by timestamp
            all_events.sort(key=lambda e: (e.get("timestamp") or 0), reverse=True)
            if limit_events and isinstance(limit_events, int):
                all_events = all_events[:limit_events]

            # Build final output applying summary/detailed logic exactly as before
            if not detailed_event_names:
                detailed_event_names = []

            final_events = []
            for ev in all_events:
                if "_dt" in ev:
                    del ev["_dt"]
                ename = ev.get("event_name")
                props = ev.get("all_event_properties", {})
                is_detailed = (ename in detailed_event_names)
                # For short summary mode, if event is not detailed, return minimal info
                if short_summary and not is_detailed:
                    event_obj = {"event_name": ename, "timestamp": ev.get("timestamp")}
                    if no_timestamp and "timestamp" in event_obj:
                        del event_obj["timestamp"]
                    final_events.append(event_obj)
                    continue

                prop_mode = detailed_props if is_detailed else global_props
                if prop_mode == "all":
                    final_props = dict(props)
                else:
                    # "custom" mode: keep only keys not starting with '$'
                    final_props = {k: v for k, v in props.items() if not k.startswith("$")}
                if exclude_props and isinstance(exclude_props, list):
                    for key_to_remove in exclude_props:
                        final_props.pop(key_to_remove, None)
                full_event = {
                    "event_name": ename,
                    "timestamp": ev.get("timestamp"),
                    "all_event_properties": final_props,
                }
                if no_timestamp and "timestamp" in full_event:
                    del full_event["timestamp"]
                final_events.append(full_event)

            return final_events

        except Exception as e:
            print(f"Exception in get_user_events: {e}")
            traceback.print_exc()
            return None

def get_event_summary_text(
    distinct_id,
    days_back=365,
    filter_event_names=None,
    start_date=None,
    end_date=None,
    limit_events=None,
    short_summary=False,
    detailed_event_names=None,
    detailed_props="all",
    global_props="all",
    no_timestamp=False,
    exclude_props=None,
    profile_properties=None
):
    """
    Helper function that creates a MixpanelDataRetriever instance, retrieves events,
    and returns a summary text (as a formatted JSON string) of the events along with
    the provided profile_properties.
    The output format replicates the original:
    {
      "profile_properties": { ... },
      "user_events": [ ... ]
    }
    """
    # Create configuration from environment variables
    config = {
        "required_settings": {
            "MIXPANEL_PROJECT_ID": os.getenv("MIXPANEL_PROJECT_ID"),
            "MIXPANEL_API_TOKEN": os.getenv("MIXPANEL_API_TOKEN"),
            "MIXPANEL_API_SECRET": os.getenv("MIXPANEL_API_SECRET"),
        }
    }
    retriever = MixpanelDataRetriever(config)
    events = retriever.get_user_events(
        distinct_id=distinct_id,
        profile_properties=profile_properties,
        days_back=days_back,
        filter_event_names=filter_event_names,
        start_date=start_date,
        end_date=end_date,
        limit_events=limit_events,
        short_summary=short_summary,
        detailed_event_names=detailed_event_names,
        detailed_props=detailed_props,
        global_props=global_props,
        no_timestamp=no_timestamp,
        exclude_props=exclude_props,
    )
    if events is None:
        events = []
    output_obj = {
        "profile_properties": profile_properties if profile_properties else {},
        "user_events": events
    }
    summary_text = json.dumps(output_obj, indent=2)
    return summary_text

# You may add additional helper functions here if needed.
