# path: mixpanel_mautic_sync/field_mapping.py

import pycountry
from dateutil.parser import parse as parse_date
from datetime import datetime

# 1) A dictionary of Mixpanel property -> Mautic field alias.
FIELD_MAPPING = {
    # Core fields (already in Mautic)
    "$email": "email",
    "$first_name": "firstname",
    "$last_name": "lastname",
    "$city": "city",
    "$region": "state",
    "$country_code": "country",  # Mixpanel: "IN" => Mautic: "India"
    "$timezone": "timezone",
    
    # Additional
    "$name": "full_name",
    "$device_id": "device_id",
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
    "userSubscribed": "user_subscribed"
}

# 2) Sets indicating which Mautic fields need special parsing
DATETIME_ALIASES = {
    "subscription_expire_date",
    "subscription_original_purchase_date",
    "subscription_purchased_date",
    "last_used"
}

NUMBER_ALIASES = {
    "total_entries",
    "job_count",
    "total_earns",
    "total_hours"
}

def convert_to_mautic_datetime(value):
    """
    Convert a date/time string from Mixpanel to Mautic's "YYYY-MM-DD HH:MM:SS" format.
    Fallback to "now" if parsing fails.
    """
    try:
        dt = parse_date(value)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def convert_to_number(value):
    """
    Convert a string (like "26.95") to float. Fallback to 0 if it fails.
    """
    try:
        return float(value)
    except:
        return 0.0

def convert_country_code_to_fullname(alpha2_code):
    """
    Use pycountry to convert a 2-letter code (e.g. "IN") into the full English name (e.g. "India").
    Returns "" if code not found or empty.
    """
    if not alpha2_code:
        return ""
    try:
        country = pycountry.countries.get(alpha_2=alpha2_code.upper())
        return country.name if country else ""
    except:
        return ""
