import aiohttp
import asyncio

async def search_yahoo(query):
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"Error: {resp.status}")
                return None
            data = await resp.json()
            return data

async def main():
    print("Yahoo Finance Stock Search Tester")
    print("Type a company name or ticker symbol (type 'exit' to quit)\n")

    while True:
        user_input = input("Search: ").strip()
        if user_input.lower() == "exit":
            break
        if not user_input:
            continue

        results = await search_yahoo(user_input)
        if not results or not results.get("quotes"):
            print("No matches found.\n")
            continue

        print("\nMatches Found:")
        for idx, item in enumerate(results["quotes"]):
            symbol = item.get("symbol", "N/A")
            name = item.get("shortname", "N/A")
            quote_type = item.get("quoteType", "N/A")
            print(f"{idx + 1}. Symbol: {symbol} | Name: {name} | Type: {quote_type}")

        best = results["quotes"][0]
        print(f"\nBest match: {best.get('symbol', 'N/A')} - {best.get('shortname', 'N/A')}\n")

if __name__ == "__main__":
    asyncio.run(main())
