# File name: test_env_and_connections.py
import os
import requests
import base64

def main():
    print("=== Test Script: Checking Environment Variables ===")

    # --- Print out or partially mask environment variables for debugging ---
    mp_project_id = os.getenv("MIXPANEL_PROJECT_ID")
    mp_token = os.getenv("MIXPANEL_API_TOKEN")
    mp_secret = os.getenv("MIXPANEL_API_SECRET")
    mautic_base_url = os.getenv("MAUTIC_BASE_URL")
    mautic_user = os.getenv("MAUTIC_USER")
    mautic_pass = os.getenv("MAUTIC_PASSWORD")

    print(f"MIXPANEL_PROJECT_ID: {mp_project_id}")
    print(f"MIXPANEL_API_TOKEN: {mp_token}")
    # For secrets, let's partially mask for safety:
    if mp_secret:
        print(f"MIXPANEL_API_SECRET (partial): {mp_secret[:4]}... (length {len(mp_secret)})")
    else:
        print("MIXPANEL_API_SECRET not found!")

    print(f"MAUTIC_BASE_URL: {mautic_base_url}")
    print(f"MAUTIC_USER: {mautic_user}")
    if mautic_pass:
        print(f"MAUTIC_PASSWORD (partial): {mautic_pass[:3]}... (length {len(mautic_pass)})")
    else:
        print("MAUTIC_PASSWORD not found!")

    print("\n=== Checking Mautic Connection ===")
    if not all([mautic_base_url, mautic_user, mautic_pass]):
        print("Mautic credentials are incomplete. Cannot test Mautic.")
    else:
        # Example call: GET /api/contacts (just to see if we can list contacts)
        url = f"{mautic_base_url}/api/contacts"
        print(f"Trying GET {url} with Basic Auth (user={mautic_user})...")
        resp = requests.get(url, auth=(mautic_user, mautic_pass))

        print(f"Mautic Response Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Success! We got a response from Mautic.")
            # Print some snippet of the JSON to verify
            try:
                data = resp.json()
                print("Mautic /contacts data snippet:", str(data)[:300], "...")
            except Exception as e:
                print(f"Failed to parse JSON from Mautic: {e}")
                print("Raw response:", resp.text[:300], "...")
        else:
            print("Error connecting to Mautic:", resp.status_code, resp.text[:300], "...")

    print("\n=== Checking Mixpanel Connection (Optional) ===")
    if mp_secret and mp_project_id:
        # We'll do a simple query to /engage?limit=1
        mp_url = "https://mixpanel.com/api/2.0/engage"
        creds = base64.b64encode(f"{mp_secret}:".encode()).decode()
        headers = {
            "Authorization": f"Basic {creds}",
            "Accept": "application/json"
        }
        params = {"project_id": mp_project_id, "limit": 1}
        print(f"Trying GET {mp_url} with project_id={mp_project_id}, limit=1 ...")
        r2 = requests.get(mp_url, headers=headers, params=params)
        print(f"Mixpanel Response Status: {r2.status_code}")
        if r2.status_code == 200:
            print("Success! Mixpanel data snippet:", r2.text[:300], "...")
        else:
            print("Error from Mixpanel:", r2.status_code, r2.text[:300], "...")
    else:
        print("No Mixpanel SECRET or PROJECT_ID found, skipping Mixpanel test.")

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
