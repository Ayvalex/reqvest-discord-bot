# Reqvest Discord Bot

Reqvest is a custom Discord bot built to help manage stock requests in a YouTube creator’s private Discord community.  

The bot allows members to request stocks, ensures each user can only vote once per stock, and provides admins with a clear tally of the most popular tickers. Requests are kept anonymous to prevent members from influencing each other’s votes.  

It was designed to solve the problem of scattered stock requests that made it difficult to identify which stocks had the most interest.  

---

## Features

- **Stock request tracking** – users can request any number of stocks, but only one vote per unique ticker will be counted. This prevents spam voting for the same stock.  
- **Anonymous requests** – votes are private to ensure fair participation and unbiased results.  
- **Ticker validation with Polygon API** – validates input against real stock names and tickers, ensuring requests are legitimate and standardized (avoids duplicates caused by typos or variations).  
- **Easy-to-use slash commands**:
  - `/request <TICKERS>` – Submit a stock request (one vote per ticker).  
  - `/help` – Learn how to use the bot.  
  - `/count` – Admin-only command to see how many times each stock has been requested so far.  
  - `/reset` – Admin-only command to clear the current cycle and start fresh.  

---

## Why This Bot?

Before Reqvest, members submitted stock ideas by casually posting in chat, which made it hard to:

- Track requests  
- Prevent multiple votes for the same stock  
- Identify which tickers had the most demand  

Polls were suggested but rejected because they restricted choices to predefined options.  

**Reqvest solved this by allowing members to freely request any stock while keeping the process organized.**

### The result:
- Increased participation in stock voting  
- Requests remain private, avoiding influence from other users’ votes  
- Clear visibility into the top-requested stocks without manual tallying  
- Streamlined workflow for the server owner to focus directly on technical analysis  

---

## Tools & Technology

- **Python 3.9+**  
- **Discord API** (via `discord.py`)  
- **Polygon API** – used to pull all stock names and tickers for validation  
- **PostgreSQL** – stores request data and voting history  

---

## Credits

- [Polygon.io](https://polygon.io) for providing stock data used to validate requests.  
