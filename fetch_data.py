import os
import requests
from supabase import create_client, Client

# Fetch credentials from GitHub Secrets
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError("Missing Supabase credentials in environment variables.")

supabase: Client = create_client(url, key)

# Dictionary of target airports and their airspace bounding boxes (lamin, lomin, lamax, lomax)
AIRPORTS = {
    "KLGA": {"lamin": 40.76, "lamax": 40.79, "lomin": -73.89, "lomax": -73.86},
    "KJFK": {"lamin": 40.62, "lamax": 40.66, "lomin": -73.80, "lomax": -73.76},
    "EWR":  {"lamin": 40.67, "lamax": 40.71, "lomin": -74.19, "lomax": -74.15},
    "KORD": {"lamin": 41.96, "lamax": 41.99, "lomin": -87.92, "lomax": -87.88}
}

def fetch_airport_traffic(code, bounds):
    api_url = f"https://opensky-network.org/api/states/all?lamin={bounds['lamin']}&lomin={bounds['lomin']}&lamax={bounds['lamax']}&lomax={bounds['lomax']}"
    
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200:
            print(f"[{code}] OpenSky HTTP Error: {response.status_code}")
            return []

        data = response.json()
        states = data.get("states", []) or []
        
        records = []
        for state in states:
            icao24 = state[0]
            callsign = state[1].strip() if state[1] else "UNKNOWN"
            on_ground = state[8]
            
            event_type = "arrival/on_ground" if on_ground else "departure/airborne"
            
            records.append({
                "airport_code": code,
                "icao24": icao24,
                "callsign": callsign,
                "event_type": event_type
            })
        
        return records
    except Exception as e:
        print(f"[{code}] Failed to fetch data: {e}")
        return []

def main():
    all_records = []
    
    for code, bounds in AIRPORTS.items():
        print(f"Fetching traffic for {code}...")
        records = fetch_airport_traffic(code, bounds)
        all_records.extend(records)
        print(f"  -> Found {len(records)} aircraft at {code}")

    if all_records:
        supabase.table("airport_flights").insert(all_records).execute()
        print(f"\nSuccessfully inserted {len(all_records)} total records into Supabase.")
    else:
        print("\nNo aircraft detected across any specified airport bounds.")

if __name__ == "__main__":
    main()
