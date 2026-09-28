import os
import requests
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError("Missing Supabase credentials in environment variables.")

supabase: Client = create_client(url, key)

AIRPORTS = {
    "KLGA": {"lamin": 40.76, "lamax": 40.79, "lomin": -73.89, "lomax": -73.86},
    "KJFK": {"lamin": 40.62, "lamax": 40.66, "lomin": -73.80, "lomax": -73.76},
    "EWR":  {"lamin": 40.67, "lamax": 40.71, "lomin": -74.19, "lomax": -74.15},
    "KORD": {"lamin": 41.96, "lamax": 41.99, "lomin": -87.92, "lomax": -87.88},
    "KSYR": {"lamin": 43.09, "lamax": 43.13, "lomin": -76.13, "lomax": -76.08}
}

def lookup_route_by_callsign(callsign):
    """
    Looks up flight route using a public callsign API fallback.
    """
    if not callsign or callsign == "UNKNOWN":
        return "UNKNOWN", "UNKNOWN"
        
    try:
        # Free public flight route lookup service
        res = requests.get(f"https://api.flightradar24.com/common/v1/search.json?query={callsign}", timeout=3)
        if res.status_code == 200:
            results = res.json().get("result", {}).get("response", {}).get("live", [])
            if results:
                flight = results[0]
                dep = flight.get("owner", {}).get("code") or "UNKNOWN"
                arr = flight.get("airport", {}).get("destination", {}).get("code", {}).get("iata") or "UNKNOWN"
                return dep, arr
    except Exception:
        pass
        
    return "N/A", "N/A"

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
            
            # Smart defaults: If plane is on ground at KSYR, arrival_airport is KSYR
            dep_airport = "UNKNOWN"
            arr_airport = code if on_ground else "EN_ROUTE"
            
            records.append({
                "airport_code": code,
                "icao24": icao24,
                "callsign": callsign,
                "event_type": event_type,
                "departure_airport": dep_airport,
                "arrival_airport": arr_airport
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
        print(f"\nSuccessfully inserted {len(all_records)} records into Supabase.")
    else:
        print("\nNo aircraft detected.")

if __name__ == "__main__":
    main()
