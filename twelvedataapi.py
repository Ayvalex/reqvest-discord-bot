import aiohttp
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('TWELVE_DATA_API_KEY')

async def search_twelve_data(query):
    url = f"https://api.twelvedata.com/symbol_search?symbol={query}&apikey={api_key}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"Error: HTTP {resp.status}")
                return None
            data = await resp.json()
            return data

async def main():
    print("Twelve Data Stock Search Tester")
    print("Type a company name or ticker symbol (type 'exit' to quit)\n")

    while True:
        user_input = input("Search: ").strip()
        if user_input.lower() == "exit":
            break
        if not user_input:
            continue

        results = await search_twelve_data(user_input)
        if not results or "data" not in results:
            print("No matches found.\n")
            continue

        print("\nMatches Found:")
        for entry in results["data"]:
            print(f"Symbol: {entry.get('symbol'):<10} | Name: {entry.get('instrument_name')} | Exchange: {entry.get('exchange')}")
        print()

if __name__ == "__main__":
    asyncio.run(main())
