import requests
import time
import json
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv('POLYGON_API_KEY')

base_url = "https://api.polygon.io/v3/reference/tickers"
limit = 1000

tickers = []
url = f"{base_url}?limit={limit}&active=true&apiKey={API_KEY}"

while url:
    print(f"Fetching: {url}")
    response = requests.get(url)
    if response.status_code == 429:
        print("Rate limit hit. Waiting 60 seconds...")
        time.sleep(60)
        continue

    data = response.json()
    tickers.extend(data.get("results", []))
    url = data.get("next_url")

    if url:
        url += f"&apiKey={API_KEY}"

    time.sleep(12)

print(f"Total tickers fetched: {len(tickers)}")

with open("tickers.json", "w") as f:
    json.dump(tickers, f, indent=2)
