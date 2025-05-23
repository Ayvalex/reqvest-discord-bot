import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from reqvestdb import init_db, add_suggestions, tally_suggestions, reset_suggestions
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

ticker_to_company = {}
for entry in ticker_data:
    for ticker in entry["tickers"]:
        ticker_to_company[ticker] = entry["name"]

company_lookup = {entry["name"]: entry["tickers"] for entry in ticker_data}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    init_db()

@bot.event
async def on_message(message):
    await bot.process_commands(message)  

    user_id = message.author.id
    if message.author.bot:
        return

    if user_id in user_states:
        state = user_states[user_id]
        current = state["current_term"]
        options = state["awaiting"][current]

        try:
            choice = int(message.content.strip()) - 1
            if 0 <= choice < len(options):
                selected = options[choice]
                state["confirmed"].append(selected)
                del state["awaiting"][current]

                if state["awaiting"]:
                    state["current_term"] = list(state["awaiting"].keys())[0]
                    next_term = state["current_term"]
                    next_options = state["awaiting"][next_term]
                    msg = f"Choose for **{next_term}**:\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(next_options))
                    await message.channel.send(msg)
                else:
                    await message.channel.send(f"Suggestions received: {', '.join(state['confirmed'])}")
                    add_suggestions(user_id, state["confirmed"], message.author.display_name)
                    del user_states[user_id]
            else:
                await message.channel.send("Invalid selection.")
        except ValueError:
            await message.channel.send("Please enter the number of your choice.")

@bot.command()
async def suggest(ctx, *, message):
    user_id = ctx.author.id
    terms = [term.strip().upper() for term in message.split(',')]
    
    awaiting = {}
    confirmed = []

    for term in terms:
        if term in ticker_to_company:
            confirmed.append(term)

        elif term in company_lookup:
            tickers = company_lookup[term]
            if len(tickers) == 1:
                confirmed.append(tickers[0])
            else:
                awaiting[term] = tickers

        else:
            match, score, _ = process.extractOne(term, company_lookup.keys(), scorer=fuzz.ratio)
            if score > 80:
                tickers = company_lookup[match]
                if len(tickers) == 1:
                    confirmed.append(tickers[0])
                else:
                    awaiting[match] = tickers
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
        add_suggestions(user_id, confirmed, member_name=ctx.author.display_name)

@bot.command()
async def tally(ctx):
    try:
        tally_result = tally_suggestions()
        if not tally_result:
            await ctx.send("No suggestions submitted yet.")
            return

        result_lines = [f"**{symbol}**: {count}" for symbol, count in tally_result]
        await ctx.send("\n".join(result_lines))
    except Exception as e:
        await ctx.send("Could not tally suggestions.")
        print(e)

@bot.command()
async def reset(ctx):
    reset_suggestions()
    await ctx.send("Votes reset.")

bot.run(token)
