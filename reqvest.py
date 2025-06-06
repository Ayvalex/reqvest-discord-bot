import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
import json
from rapidfuzz import process, fuzz
import re
from collections import defaultdict
from discord.ui import View, Select
from datetime import datetime, time, timedelta
import pytz

TORONTO_TZ = pytz.timezone('America/Toronto')
PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

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

        self.db = None

    async def setup_hook(self):
        from reqvestdb import Database
        
        host=os.getenv("DB_HOST")
        database=os.getenv("DB_NAME")
        user=os.getenv("DB_USER")
        password=os.getenv("DB_PASSWORD")

        self.db = Database(host, database, user, password)
        self.db.create_tables()
        await self.tree.sync()

bot = MyBot()

user_states = {}

class TickerSelect(Select):
    def __init__(self, options, user_id, state):
        super().__init__(placeholder="Choose a ticker", min_values=1, max_values=1, options=[discord.SelectOption(label=o) for o in options])
        self.user_id = user_id
        self.state = state

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        self.state["confirmed"].append(selected)
        del self.state["awaiting"][self.state["current_request"]]

        self.disabled = True
        await interaction.response.edit_message(view=self.view)

        if self.state["awaiting"]:
            self.state["current_request"] = next(iter(self.state["awaiting"]))
            await interaction.followup.send(
                f"Multiple tickers found for {self.state['current_request']}:",
                view=TickerView(self.user_id, self.state),
                ephemeral=True
            )
        else:
            bot.db.add_member_requests(interaction.guild_id, self.user_id, self.state["confirmed"], interaction.user.display_name)
            await interaction.followup.send(f"Requests received: {', '.join(self.state['confirmed'])}", ephemeral=True)
            #await interaction.channel.send(f"{interaction.user.mention} submitted stock requests!")
            del user_states[self.user_id]

class TickerView(View):
    def __init__(self, user_id, state):
        super().__init__(timeout=None)
        self.select = TickerSelect(state["awaiting"][state["current_request"]], user_id, state)
        self.add_item(self.select)

def clean_company_name(name):
    pattern = r"(\\|/|,|\bCORP\b|\bCORPORATION|\bINC\b|\bINTERNATIONAL\b|\bSYSTEMS\b|\bLABORATORIES\b|\bTRUST\b|\bTECHNOLOGIES\b|\bTECHNOLOGY\b|\bCOMPANIES\b|\bWHOLESALE\b|\bMARKETS\b|\bPLC\b|\bGROUP\b|\bNV\b|\bA\sS\b|\bCO\b|&\sCO\b|&\sCOMPANY\b|\bCOMMUNICATIONS\b|\bUFJ\b|\bSE\b|\bINBEV\b|\bFINANCIAL\b|\bHOLDING|\bLTD\b|\bLLC\b|\bCOM\b|\bAG\b).*"
    return re.sub(pattern, "", name, flags=re.IGNORECASE).strip().upper()

def build_company_data(filepath):
    with open(filepath, "r") as f:
        raw_data = json.load(f)

    company_map = defaultdict(list)
    
    for entry in raw_data.values():
        if "ticker" in entry and "title" in entry:
            name = clean_company_name(entry["title"])
            # name = entry["title"].strip().upper()
            ticker = entry["ticker"].upper()
            company_map[name].append(ticker)

    company_to_ticker = {name: sorted(tickers) for name, tickers in company_map.items()}
    ticker_to_company = {ticker: name for name, tickers in company_to_ticker.items() for ticker in tickers}

    return company_to_ticker, ticker_to_company

company_to_ticker, ticker_to_company = build_company_data("company_tickers.json")

""" @tasks.loop(minutes=1)
async def daily_reminder():
    now = datetime.now(PACIFIC_TZ)

    if now.weekday() < 6 and now.time().hour == 3 and now.time().minute == 7:
        for guild in bot.guilds:
            channel = guild.text_channels[0]  # Only channel bot has access to
            try:
                await channel.send("Friendly reminder: Stock analyses are done over the **weekend**. Submit your stock requests using /request before [cutoff time]!")
            except discord.Forbidden:
                pass """

@bot.event
async def on_ready():
    pass
    # if not daily_reminder.is_running():
    #     daily_reminder.start()

def process_requests(requests):
    confirmed = []
    awaiting = {}
    no_matches = []

    for request in requests:
        if request in ticker_to_company:
            confirmed.append(request)
        elif request in company_to_ticker:
            tickers = company_to_ticker[request]
            if len(tickers) == 1:
                confirmed.append(tickers[0])
            else:
                awaiting[request] = tickers
        else:
            match, score, _ = process.extractOne(request, company_to_ticker.keys(), scorer=fuzz.partial_ratio)
            if score > 80:
                tickers = company_to_ticker[match]
                if len(tickers) == 1:
                    confirmed.append(tickers[0])
                else:
                    awaiting[match] = tickers
            else:
                no_matches.append(request)

    return confirmed, awaiting, no_matches

def is_valid_request(text):
    text = text.strip()
    
    return bool(re.search(r"[a-zA-Z]", text))

@bot.tree.command(name="request", description="Request one or more stocks by name or ticker")
@app_commands.describe(stocks="Enter any number of stock names or tickers, separated by commas (e.g. Apple, TSLA, Nvidia)")
async def request(interaction: discord.Interaction, stocks: str):
    requests = [s.strip().upper() for s in stocks.split(",")]
        
    if not requests:
        await interaction.response.send_message("No valid stock name or ticker found. Please use commas to separate requests.")
        return
    
    valid_requests = [r for r in requests if is_valid_request(r)]
    
    if not valid_requests:
        await interaction.response.send_message("No valid stock names or tickers detected. Please use company names or ticker symbols.", ephemeral=True)
        return
    
    user_id = interaction.user.id
    #confirmed, awaiting, no_matches = process_requests(requests)
    confirmed, awaiting, no_matches = process_requests(valid_requests)

    messages = []

    if confirmed:
        bot.db.add_member_requests(interaction.guild_id, user_id, confirmed, interaction.user.display_name)
        messages.append(f"Requests received: {', '.join(confirmed)}")
        if not awaiting:
            await interaction.channel.send(f"{interaction.user.mention} submitted stock requests!", delete_after=43200)

    if no_matches:
        messages.append(f"No match found for: {', '.join(no_matches)}")
        messages.append(f"Please check spelling or try using the stock's ticker symbol.")

    if awaiting:
        user_states[user_id] = {
            "awaiting": awaiting,
            "confirmed": confirmed,
            "current_request": next(iter(awaiting))
        }
        await interaction.response.send_message(
        f"Multiple tickers found for {user_states[user_id]['current_request']}:",
        view=TickerView(user_id, user_states[user_id]), ephemeral=True)
    else:
        await interaction.response.send_message("\n".join(messages), ephemeral=True)
        
@bot.tree.command(name="count", description="Show the count of all ticker requests.")
async def count(interaction: discord.Interaction):
    tally = bot.db.requests_count(interaction.guild_id) 

    if not tally:
        await interaction.response.send_message("No requests have been made yet.")
        return

    message_lines = [f"**Vote Counts Per Requested Ticker:**"]
    for index, (ticker, count) in enumerate(tally, start=1):
        message_lines.append(f"{index}. **{ticker}**: {count} vote{'s' if count != 1 else ''}")

    message = "\n".join(message_lines)
    await interaction.response.send_message(message)

""" def get_upcoming_sunday_date():
    today = datetime.now()
    days_ahead = (6 - today.weekday()) % 7  # Sunday = 6
    upcoming_sunday = today + timedelta(days=days_ahead)
    return upcoming_sunday.strftime("%m/%d") """

def get_upcoming_sunday_date():
    today = datetime.now()
    days_ahead = (6 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  
    upcoming_sunday = today + timedelta(days=days_ahead)
    return upcoming_sunday.strftime("%m/%d")

@bot.tree.command(name="reset", description="Reset all requests.")
async def reset(interaction: discord.Interaction):
    bot.db.reset_all_data(interaction.guild_id)
    await interaction.response.send_message("All requests have been cleared.\n New ones can now be submitted for next week’s chart analyses.", ephemeral=True)

@bot.tree.command(name="help", description="Learn how to use the Request Bot.")
async def help(interaction: discord.Interaction):
    help_message = (
        "Use the `/request` command to submit one or more stock tickers or company names.\n"
        "- Separate multiple entries with commas.\n"
        "- You can use either full company names or ticker symbols (e.g., `AAPL`, `Tesla`).\n"
        "- If a name matches multiple tickers, you’ll be prompted to choose the correct one.\n"
        "- Only __one vote per stock__ will be counted per user — duplicate entries are ignored.\n"
    )
    await interaction.response.send_message(help_message, ephemeral=True)
    
bot.run(token)
