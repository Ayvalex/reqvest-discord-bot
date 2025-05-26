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

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

user_states = {}

def clean_company_name(name):
    pattern = r"(\\|/|,|\bCORP\b|\bCORPORATION|\bINC\b|\bLTD\b|\bLLC\b|\bCOM\b|\bAG\b|\b(?:[A-Z]\.){2,}).*"
    return re.sub(pattern, "", name, flags=re.IGNORECASE).strip().upper()

def build_company_data(filepath):
    with open(filepath, "r") as f:
        raw_data = json.load(f)

    company_map = defaultdict(list)
    
    for entry in raw_data.values():
        if "ticker" in entry and "title" in entry:
            name = clean_company_name(entry["title"])
            ticker = entry["ticker"].upper()
            company_map[name].append(ticker)

    company_to_ticker = {name: sorted(tickers) for name, tickers in company_map.items()}
    ticker_to_company = {ticker: name for name, tickers in company_to_ticker.items() for ticker in tickers}

    return company_to_ticker, ticker_to_company

company_to_ticker, ticker_to_company = build_company_data("company_tickers.json")

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

def process_suggestions(suggestions):
    confirmed = []
    awaiting = {}

    for suggestion in suggestions:
        if suggestion in ticker_to_company:
            confirmed.append(suggestion)
        elif suggestion in company_to_ticker:
            tickers = company_to_ticker[suggestion]
            if len(tickers) == 1:
                confirmed.append(tickers[0])
            else:
                awaiting[suggestion] = tickers
        else:
            match, score, _ = process.extractOne(suggestion, company_to_ticker.keys(), scorer=fuzz.ratio)
            if score > 80:
                tickers = company_to_ticker[match]
                if len(tickers) == 1:
                    confirmed.append(tickers[0])
                else:
                    awaiting[match] = tickers
            else:
                confirmed.append(f"[NO MATCH: {suggestion}]")

    return confirmed, awaiting

async def prompt_next_suggestion(target, user_id):
    state = user_states[user_id]
    suggestion = state["current_term"]
    options = state["awaiting"][suggestion]
    msg = f"Multiple tickers found for {suggestion}:\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(options))

    if isinstance(target, discord.Interaction):
        await target.response.send_message(msg)
    else:
        await target.send(msg)

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