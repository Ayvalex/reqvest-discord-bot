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
        super().__init__(
            placeholder="Choose a ticker",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=o) for o in options]
        )
        self.user_id = user_id
        self.state = state

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        selected = self.values[0]
        self.state["confirmed"].append(selected)
        del self.state["awaiting"][self.state["current_request"]]

        self.disabled = True

        await interaction.edit_original_response(view=self.view)

        if self.state["awaiting"]:
            self.state["current_request"] = next(iter(self.state["awaiting"]))
            await interaction.followup.send(
                f"Multiple tickers found for {self.state['current_request']}:",
                view=TickerView(self.user_id, self.state),
                ephemeral=True
            )
        else:
            bot.db.add_member_requests(
                interaction.guild_id,
                self.user_id,
                self.state["confirmed"],
                interaction.user.display_name
            )

            await interaction.followup.send(
                f"Requests received: {', '.join(self.state['confirmed'])}",
                ephemeral=True
            )

            await interaction.channel.send(
                f"{interaction.user.mention} submitted stock requests!"
            )

            del user_states[self.user_id]


class TickerView(View):
    def __init__(self, user_id, state):
        super().__init__(timeout=None)
        self.select = TickerSelect(state["awaiting"][state["current_request"]], user_id, state)
        self.add_item(self.select)


def clean_company_name(name):
    name = re.sub(r'[,\s]*\bNew\b\s*$', '', name, flags=re.IGNORECASE)

    name = re.sub(
        r'\b(Corporation|Corp\.?|Inc\.?|Incorporated|Ltd\.?|LLC|PLC|S\.A\.|L\.P\.|Group|Holdings?|'
        r'Company|Co\.?|Class [A-Z]+|Series [A-Z0-9]+|Units?|Warrants?|ETF.*?|Depositary Shares.*?|'
        r'Common Stock|Preferred Stock|Ordinary Shares|American Depositary Shares)\b',
        '',
        name,
        flags=re.IGNORECASE
    )

    name = re.sub(r'[^A-Za-z0-9\s]', '', name)

    name = re.sub(r'\s+', ' ', name).strip()

    return name.upper()


def build_company_data(filepath):
    with open(filepath, "r") as f:
        raw_data = json.load(f)

    company_map = defaultdict(list)
    
    for entry in raw_data:
        if entry["market"] not in ["indices", "otc", "fx"]:
            name = clean_company_name(entry["name"])
            # name = entry["title"].strip().upper()
            ticker = entry["ticker"].upper()
            company_map[name].append(ticker)

    company_to_ticker = {name: sorted(tickers) for name, tickers in company_map.items()}
    ticker_to_company = {ticker: name for name, tickers in company_to_ticker.items() for ticker in tickers}

    return company_to_ticker, ticker_to_company

company_to_ticker, ticker_to_company = build_company_data("tickers.json")


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


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.db.has_user_voted(message.guild.id, message.author.id):
        return
    
    try:
        embed = discord.Embed(
            description=(
                f"{message.author.mention} — want to make stock requests?\n\n"
                "Use `/request` to submit picks.\n"
                "Use `/help` if you're unsure.\n"
                "Top 10 tickers get charted every **Sunday**."
            ),
            color=discord.Color.blurple() 
        )
        await message.channel.send(embed=embed, delete_after=20)
    except discord.Forbidden:
        pass

    await bot.process_commands(message) 


""" def company_name_scorer(query, choice, **kwargs):
    return (
        0.5 * fuzz.partial_ratio(query, choice)
        + 0.3 * fuzz.token_set_ratio(query, choice)
        + 0.2 * fuzz.ratio(query, choice)
    ) """

def company_name_scorer(query, choice, **kwargs):
    return (
        0.35 * fuzz.partial_token_set_ratio(query, choice)
        + 0.25 * fuzz.partial_ratio(query, choice)
        + 0.2 * fuzz.token_sort_ratio(query, choice)
        + 0.1 * fuzz.ratio(query, choice)
        + 0.1 * fuzz.WRatio(query, choice)
    )


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
            match, score, _ = process.extractOne(request, company_to_ticker.keys(), scorer=company_name_scorer)
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
    await interaction.response.defer(ephemeral=True)

    requests = [s.strip().upper() for s in stocks.split(",")]
    valid_requests = [r for r in requests if is_valid_request(r)]

    if not valid_requests:
        await interaction.followup.send(
            "No valid stock names or tickers detected. Please use company names or ticker symbols.",
            ephemeral=True
        )
        return

    user_id = interaction.user.id
    confirmed, awaiting, no_matches = process_requests(valid_requests)

    messages = []

    if confirmed:
        bot.db.add_member_requests(interaction.guild_id, user_id, confirmed, interaction.user.display_name)
        messages.append(f"Requests received: {', '.join(confirmed)}")

        if not awaiting:
            await interaction.channel.send(
                f"{interaction.user.mention} submitted stock requests!"
            )

    if no_matches:
        messages.append(f"No match found for: {', '.join(no_matches)}")
        messages.append("Please check spelling or try using the stock's ticker symbol.")

    if awaiting:
        user_states[user_id] = {
            "awaiting": awaiting,
            "confirmed": confirmed,
            "current_request": next(iter(awaiting))
        }

        await interaction.followup.send(
            f"Multiple tickers found for {user_states[user_id]['current_request']}:",
            view=TickerView(user_id, user_states[user_id]),
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            "\n".join(messages) if messages else "Done.",
            ephemeral=True
        )

        
@bot.tree.command(name="count", description="Show the count of all ticker requests.")
async def count(interaction: discord.Interaction):
    tally = bot.db.requests_count(interaction.guild_id)

    if not tally:
        embed = discord.Embed(
            title="No Stock Requests Yet",
            description="No stock requests have been made so far. Use `/request` to submit your picks!",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        return

    vote_lines = [
        f"{i+1:>2}. **{ticker}** — {count} vote{'s' if count != 1 else ''}"
        for i, (ticker, count) in enumerate(tally)
    ]

    embed = discord.Embed(
        title="Vote Counts Per Requested Ticker:",
        description="\n".join(vote_lines),
        color=discord.Color.teal()
    )

    await interaction.response.send_message(embed=embed)


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

    upcoming_sunday = get_upcoming_sunday_date()

    confirmation_embed = discord.Embed(
        title="Requests Reset",
        description="All requests have been **cleared**.",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)

    role = discord.utils.get(interaction.guild.roles, name="Tier 3: Xtra stocks/Chart Request")
    if role:
        mention = role.mention  
    else:
        mention = "Tier 3: Xtra stocks/Chart Request"

    announcement_embed = discord.Embed(
        title="📢 NEW REQUEST CYCLE HAS BEGUN!",
        description=(
            "**All previous requests have been cleared.**\n\n"
            "Type `/` and choose `request` to make submissions.\n\n"
            f"Cast your picks by Sunday (**{upcoming_sunday}**, Eastern Time)!\n\n"
            "Top 10 most requested will be analyzed on Sunday.\n\n"
            "Need help? Use `/help`."
        ),
        color=discord.Color.green()
    )

    try:
        await interaction.channel.send(content=mention)
        await interaction.channel.send(embed=announcement_embed)
    except discord.Forbidden:
        pass


@bot.tree.command(name="help", description="Learn how to use the Request Bot.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="How to Use the Request Bot",
        description=(
            "Use the `/request` command to submit one or more **stock tickers** or **company names**."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Instructions",
        value=(
            "• Separate multiple entries with commas.\n"
            "• Use full company names or ticker symbols (e.g., `AAPL`, `Tesla`).\n"
            "• If a name matches multiple tickers, you'll be asked to pick the correct one.\n"
            "• Only __one vote per stock__ is counted per user — duplicates are ignored."
        ),
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(token)
