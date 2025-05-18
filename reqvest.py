import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging

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

@bot.event
async def on_ready():
    logger.info(f"Bot connected as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    logger.info(f"Received message from {message.author}: {message.content}")
    await bot.process_commands(message)

@bot.command()
async def suggest(ctx, *, message):
    stock_input = message.upper().replace(' ', '')
    stock_list = list(set(stock_input.split(',')))

    if not stock_list:
        await ctx.send("Please provide at least one stock symbol.")
        return

    #add_suggestions(str(ctx.author.id), stock_list)
    await ctx.send(f"Suggestions received: {', '.join(stock_list)}")

bot.run(token)