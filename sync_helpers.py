# sync_helpers.py

import os
import json
import requests
import base64
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse as parse_date

LAST_RUN_FILE = "last_run.json"

def get_country_code_from_country(country_name):
    """Map full country names to ISO codes."""
    country_mapping = {
        'United States': 'US',
        'United Kingdom': 'GB',
        'Australia': 'AU',
        'Canada': 'CA',
        'India': 'IN',
        'Germany': 'DE',
        'France': 'FR',
        'Italy': 'IT',
        'Spain': 'ES',
        'Netherlands': 'NL',
        'Belgium': 'BE',
        'Switzerland': 'CH',
        'Austria': 'AT',
        'Sweden': 'SE',
        'Denmark': 'DK',
        'Norway': 'NO',
        'Finland': 'FI',
        'Ireland': 'IE',
        'Japan': 'JP',
        'China': 'CN',
        'Singapore': 'SG',
        'Hong Kong': 'HK',
        'Taiwan': 'TW',
        'Indonesia': 'ID',
        'Russia': 'RU',
        'Turkey': 'TR',
        'Israel': 'IL',
        'South Africa': 'ZA',
        'Saudi Arabia': 'SA',
        'United Arab Emirates': 'AE',
        'Luxembourg': 'LU',
        'Malta': 'MT',
        'Cyprus': 'CY',
        'Bulgaria': 'BG',
        'Estonia': 'EE',
        'Slovakia': 'SK',
        'Czech Republic': 'CZ',
        'Latvia': 'LV',
        'Lithuania': 'LT',
        'Slovenia': 'SI',
        'Greece': 'GR',
        'Poland': 'PL',
        'Portugal': 'PT',
        'Romania': 'RO',
        'Hungary': 'HU'
    }
    return country_mapping.get(country_name, 'US')  # Default to US if unknown

def get_env_var(key, default=None):
    return os.getenv(key, default)

def load_last_run_time():
    if os.path.exists(LAST_RUN_FILE):
        with open(LAST_RUN_FILE, "r") as f:
            data = json.load(f)
            return data.get("last_run_time")
    day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    return day_ago

def save_last_run_time(dt_iso):
    with open(LAST_RUN_FILE, "w") as f:
        json.dump({"last_run_time": dt_iso}, f)

def get_mixpanel_headers():
    mp_secret = get_env_var("MIXPANEL_API_SECRET")
    if not mp_secret:
        raise ValueError("MIXPANEL_API_SECRET not found.")
    creds = base64.b64encode(f"{mp_secret}:".encode()).decode()
    return {
        "Authorization": f"Basic {creds}",
        "Accept": "application/json"
    }

def fetch_profiles_for_created_date(date_str):
    mp_project_id = get_env_var("MIXPANEL_PROJECT_ID")
    if not mp_project_id:
        raise ValueError("MIXPANEL_PROJECT_ID not found in env")
    where_clause = (
       f'properties["$created"] >= "{date_str}T00:00:00" '
       f'and properties["$created"] < "{date_str}T23:59:59"'
    )
    url = "https://mixpanel.com/api/2.0/engage"
    params = {
        "project_id": mp_project_id,
        "where": where_clause,
        "limit": 1000
    }
    print(f"[Mixpanel] Fetching profiles CREATED on {date_str}, limit=1000")
    resp = requests.get(url, headers=get_mixpanel_headers(), params=params)
    if resp.status_code != 200:
        print(f"[ERROR] Mixpanel Fetch: Error {resp.status_code} when fetching day={date_str}")
        return []
    data = resp.json()
    results = data.get("results", [])
    profiles = []
    for r in results:
        p = r.get("$properties", {})
        p["distinct_id"] = r.get("$distinct_id")
        profiles.append(p)
    print(f"[Mixpanel] Found {len(profiles)} newly created profiles for {date_str}")
    return profiles

def fetch_profiles_since_last_run():
    last_run_iso = load_last_run_time()
    mp_project_id = get_env_var("MIXPANEL_PROJECT_ID")
    if not mp_project_id:
        raise ValueError("MIXPANEL_PROJECT_ID not found")
    where_clause = f'properties["$last_seen"] >= "{last_run_iso}"'
    url = "https://mixpanel.com/api/2.0/engage"
    params = {
        "project_id": mp_project_id,
        "where": where_clause,
        "limit": 100
    }
    print(f"[Mixpanel] Incremental fetch updated >= {last_run_iso}")
    resp = requests.get(url, headers=get_mixpanel_headers(), params=params)
    if resp.status_code != 200:
        print(f"[ERROR] Mixpanel Fetch: Error {resp.status_code} for incremental")
        return []
    data = resp.json()
    results = data.get("results", [])
    profiles = []
    for r in results:
        p = r.get("$properties", {})
        p["distinct_id"] = r.get("$distinct_id")
        profiles.append(p)
    print(f"[Mixpanel] Found {len(profiles)} profiles since {last_run_iso}")
    return profiles

def get_mautic_auth():
    user = get_env_var("MAUTIC_USER")
    pw = get_env_var("MAUTIC_PASSWORD")
    if not user or not pw:
        raise ValueError("MAUTIC_USER/MAUTIC_PASSWORD not found.")
    return (user, pw)

def post_mautic_contact(top_level_data, distinct_id=None):
    base_url = get_env_var("MAUTIC_BASE_URL")
    if not base_url:
        raise ValueError("MAUTIC_BASE_URL missing.")
    url = f"{base_url}/api/contacts/new"
    print(f"[Mautic] POST {url} data: {top_level_data}")
    resp = requests.post(
        url,
        auth=get_mautic_auth(),
        headers={"Content-Type": "application/json"},
        json=top_level_data
    )
    if resp.status_code not in (200, 201):
        print(f"[ERROR] Mautic POST: Error {resp.status_code} for {distinct_id}")
    return resp

def patch_mautic_contact(mautic_id, top_level_data, distinct_id=None):
    base_url = get_env_var("MAUTIC_BASE_URL")
    url = f"{base_url}/api/contacts/{mautic_id}/edit"
    print(f"[Mautic] PATCH {url} data: {top_level_data}")
    resp = requests.patch(
        url,
        auth=get_mautic_auth(),
        headers={"Content-Type": "application/json"},
        json=top_level_data
    )
    if resp.status_code not in (200, 201, 404):
        print(f"[ERROR] Mautic PATCH: Error {resp.status_code} for {distinct_id}")
    return resp

def parse_mautic_id(mautic_response_json):
    return mautic_response_json.get("contact", {}).get("id")

def map_mixpanel_to_mautic(mixpanel_dict):
    from field_mapping import (
        FIELD_MAPPING,
        DATETIME_ALIASES,
        NUMBER_ALIASES,
        convert_to_mautic_datetime,
        convert_to_number,
        convert_country_code_to_fullname
    )
    from price_calculator import PriceCalculator

    mapped = {}
    
    # Basic field mapping
    for mp_prop, mautic_alias in FIELD_MAPPING.items():
        if mp_prop in mixpanel_dict:
            raw_val = mixpanel_dict[mp_prop]
            if mautic_alias in DATETIME_ALIASES and raw_val:
                val = convert_to_mautic_datetime(raw_val)
            elif mautic_alias in NUMBER_ALIASES and raw_val not in (None, ""):
                val = convert_to_number(raw_val)
            elif mautic_alias == "country":
                val = convert_country_code_to_fullname(raw_val)
            else:
                val = raw_val
            mapped[mautic_alias] = val

    # Standard fields
    mapped["ipAddress"] = mixpanel_dict.get("$ip", "127.0.0.1")
    last_seen_raw = mixpanel_dict.get("$last_seen", "")
    if last_seen_raw:
        mapped["lastActive"] = convert_to_mautic_datetime(last_seen_raw)
    else:
        mapped["lastActive"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mapped["overwriteWithBlank"] = ""
    mapped["owner"] = "1"
    if "email" in mapped and isinstance(mapped["email"], str):
        mapped["email"] = mapped["email"].lower().strip()

    # Initialize variables outside try block
    country_name = mixpanel_dict.get("country") or mixpanel_dict.get("$country", "")
    country_code = None
    subscription_plan = mixpanel_dict.get("subscription_plan", "")

    # Add pricing calculations
    try:
        calculator = PriceCalculator()
        
        # Get country code - try all possible country fields and formats
        country_code = (
            mixpanel_dict.get("$country_code") or 
            mixpanel_dict.get("country_code") or 
            get_country_code_from_country(country_name)
        )
        
        print(f"[DEBUG] Country detection: name='{country_name}', code='{country_code}'")
        
        # Calculate pricing based on subscription plan
        if "weeklyNew2" in subscription_plan:
            pricing = calculator.calculate_savings(4.99, 49.99, country_code)
            mapped["pricing_display"] = {
                "current_plan": "weekly",
                "current_usd": calculator.format_price(4.99, "USD"),
                "current_local": calculator.format_price(pricing['local']['original'], pricing['local']['currency']),
                "yearly_usd": calculator.format_price(49.99, "USD"),
                "yearly_local": calculator.format_price(pricing['local']['target'], pricing['local']['currency']),
                "savings_usd": calculator.format_price(pricing['usd']['savings'], "USD"),
                "savings_local": calculator.format_price(pricing['local']['savings'], pricing['local']['currency']),
                "currency_code": pricing['local']['currency']
            }
        elif "monthlyNew" in subscription_plan:
            pricing = calculator.calculate_savings(6.99, 49.99, country_code)
            mapped["pricing_display"] = {
                "current_plan": "monthly",
                "current_usd": calculator.format_price(6.99, "USD"),
                "current_local": calculator.format_price(pricing['local']['original'], pricing['local']['currency']),
                "yearly_usd": calculator.format_price(49.99, "USD"),
                "yearly_local": calculator.format_price(pricing['local']['target'], pricing['local']['currency']),
                "savings_usd": calculator.format_price(pricing['usd']['savings'], "USD"),
                "savings_local": calculator.format_price(pricing['local']['savings'], pricing['local']['currency']),
                "currency_code": pricing['local']['currency']
            }
        else:
            # Free plan pricing info
            weekly_prices = calculator.get_prices_for_country(4.99, country_code)
            mapped["pricing_display"] = {
                "current_plan": "free",
                "weekly_usd": calculator.format_price(4.99, "USD"),
                "weekly_local": calculator.format_price(weekly_prices[1], weekly_prices[2]),
                "currency_code": weekly_prices[2]
            }
        
        print(f"[DEBUG] Pricing calculated for {country_code}: {json.dumps(mapped['pricing_display'], indent=2)}")
        
    except Exception as e:
        print(f"[ERROR] Price calculation failed: {str(e)}")
        print(f"[ERROR] Profile data for pricing: country='{country_name}', code='{country_code}', plan='{subscription_plan}'")
        mapped["pricing_display"] = None

    return mapped