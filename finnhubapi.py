import aiohttp
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('FINNHUB_API_KEY')

async def search_finnhub(query):
    url = f"https://finnhub.io/api/v1/search?q={query}&token={api_key}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"Error: {resp.status}")
                return None
            data = await resp.json()
            return data

async def main():
    print("Finnhub Stock Search Tester")
    print("Type a company name or ticker symbol (type 'exit' to quit)\n")

    while True:
        user_input = input("Search: ").strip()
        if user_input.lower() == "exit":
            break
        if not user_input:
            continue

        results = await search_finnhub(user_input)
        if not results or not results.get("result"):
            print("No matches found.\n")
            continue

        print("\nMatches Found:")
        for idx, item in enumerate(results["result"]):
            print(f"{idx + 1}. Symbol: {item.get('symbol')} | Name: {item.get('description')} | Type: {item.get('type')}")

        print(f"\nBest match: {results['result'][0].get('symbol')} - {results['result'][0].get('description')}\n")

if __name__ == "__main__":
    asyncio.run(main())