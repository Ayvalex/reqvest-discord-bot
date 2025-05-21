import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from reqvestdb import init_db, add_suggestions, tally_suggestions
import json
from rapidfuzz import process, fuzz
import re

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

with open("company_tickers.json", "r") as f:
    raw_data = json.load(f)

def clean_company_name(name):
    name = re.sub(r"(\\|/|,|\bCORP\b|\bCORPORATION|\bINC\b|\bLTD\b|\bLLC\b|\bCOM\b|\bAG\b|\b(?:[A-Z]\.){2,}).*", "", name, flags=re.IGNORECASE)
    return name.strip().upper()

transformed = [
    {"symbol": entry["ticker"], "name": clean_company_name(entry["title"])}
    for entry in raw_data.values()
    if "ticker" in entry and "title" in entry
]

with open("tickers_cleaned.json", "w") as f:
    json.dump(transformed, f, indent=2)

with open("tickers_cleaned.json", "r") as f:
    ticker_data = json.load(f)

symbol_set = {entry["symbol"].upper() for entry in ticker_data}
name_to_symbol = {entry["name"].upper(): entry["symbol"] for entry in ticker_data}
company_names = list(name_to_symbol.keys())

def resolve_to_symbol(user_input, confidence_threshold=75):
    query = user_input.strip().upper()

    if query in symbol_set:
        return query  

    match = process.extractOne(user_input.strip(), company_names, scorer=fuzz.token_sort_ratio)
    if match and match[1] >= confidence_threshold:
        return name_to_symbol[match[0]]

    return None 

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    init_db()

@bot.command()
async def suggest(ctx, *, message=""):
    if not message:
        await ctx.send("Please provide at least one stock symbol.")
        return
    
    stock_input = message.upper().replace(' ', '')
    stock_list = list(set(stock_input.split(',')))

    if not stock_list:
        await ctx.send("Please provide at least one stock symbol.")
        return

    member_name = str(ctx.author.name)

    checked_stock_list = []
    for suggestion in stock_list:
        result = resolve_to_symbol(suggestion)
        if result is not None:
            checked_stock_list.append(result)

    if not checked_stock_list:
        await ctx.send("None of your suggestions were recognized as valid tickers.")
        return

    try:
        add_suggestions(member_name, checked_stock_list)
        await ctx.send(f"Suggestions received: {', '.join(checked_stock_list)}")
    except Exception as e:
        await ctx.send("There was an error saving your suggestion.")
        print(e)

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