import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from reqvestdb import init_db, add_suggestions, tally_suggestions
import json
from rapidfuzz import process, fuzz
import re
from collections import defaultdict

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('reqvest_bot')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
user_states = {}

with open("company_tickers.json", "r") as f:
    raw_data = json.load(f)

def clean_company_name(name):
    name = re.sub(r"(\\|/|,|\bCORP\b|\bCORPORATION|\bINC\b|\bLTD\b|\bLLC\b|\bCOM\b|\bAG\b|\b(?:[A-Z]\.){2,}).*", "", name, flags=re.IGNORECASE)

    return name.strip().upper()

company_map = defaultdict(list)

for entry in raw_data.values():
    if "ticker" in entry and "title" in entry:
        name = clean_company_name(entry["title"])
        ticker = entry["ticker"].upper()
        company_map[name].append(ticker)

transformed = [{"name": name, "tickers": sorted(tickers)} for name, tickers in company_map.items()]

with open("tickers_cleaned.json", "w") as f:
    json.dump(transformed, f, indent=2)

with open("tickers_cleaned.json", "r") as f:
    ticker_data = json.load(f)

#symbol_set = {entry["symbol"].upper() for entry in ticker_data}
company_lookup = {entry["name"].lower(): entry["tickers"] for entry in ticker_data}
#company_names = list(name_to_symbol.keys())

""" company_lookup = {
    "alphabet": ["GOOG", "GOOGL"],
    "berkshire": ["BRK.A", "BRK.B"],
    "microsoft": ["MSFT"]
}


user_states = {
    1234567890: {  # User ID
        "awaiting": {
            "alphabet": ["GOOG", "GOOGL"],
            "berkshire": ["BRK.A", "BRK.B"]
        },
        "confirmed": [],
        "current_term": "alphabet"
    }
} """

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    init_db()

@bot.command()
async def suggest(ctx, *, message):
    user_id = ctx.author.id
    terms = [term.strip().lower() for term in message.split(',')]
    
    awaiting = {}
    confirmed = []

    for term in terms:
        tickers = company_lookup.get(term)
        if tickers:
            if len(tickers) == 1:
                confirmed.append(tickers[0])
            else:
                awaiting[term] = tickers
        else:
            await ctx.send(f"No match found for '{term}'.")

    if awaiting:
        user_states[user_id] = {
            "awaiting": awaiting,
            "confirmed": confirmed,
            "current_term": list(awaiting.keys())[0]
        }
        current = user_states[user_id]["current_term"]
        options = user_states[user_id]["awaiting"][current]
        msg = f"Multiple tickers found for **{current}**:\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(options))
        await ctx.send(msg)
    else:
        await ctx.send(f"Suggestions received: {', '.join(confirmed)}")
        
@bot.command()
async def tally(ctx):
    try:
        tally_result = tally_suggestions()
        if not tally_result:
            await ctx.send("No suggestions submitted yet.")
            return

        result_lines = [f"**{symbol}**: {count} vote(s)" for symbol, count in tally_result]
        await ctx.send("\n".join(result_lines))
    except Exception as e:
        await ctx.send("Could not tally suggestions.")
        print(e)

bot.run(token)