# c:\CryptoBot\crypto_bot\x_query_ta_v9_new.py
import os
import logging
import asyncio
import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv
import schedule
from datetime import datetime, timezone
import pytz
import sys

# Add the crypto_bot directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Local imports (using relative imports)
from .modules.database_utils import DatabaseManager
from .modules.coin_data import fetch_all_data
from .modules.news_utils import fetch_news
from .modules.youtube_utils import fetch_youtube_videos
from .modules.santiment_utils import fetch_santiment_metrics
from .modules.social_media_utils import follow_crypto_users, post_x_thread
from .modules.content_utils import post_discord_update, create_thread_content

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_test.log'),
        logging.StreamHandler()
    ]
)
lg = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')
X_BEARER_TOKEN = os.getenv('X_BEARER_TOKEN')
X_ACCESS_TOKEN = os.getenv('X_ACCESS_TOKEN')
X_ACCESS_TOKEN_SECRET = os.getenv('X_ACCESS_TOKEN_SECRET')
X_API_KEY = os.getenv('X_API_KEY')
X_API_SECRET = os.getenv('X_API_SECRET')

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Database setup
db_manager = DatabaseManager('crypto_bot.db')

# Initialize X client
def initialize_x_client():
    """Initialize and return the X client using Tweepy."""
    try:
        import tweepy
        x_client = tweepy.Client(
            bearer_token=X_BEARER_TOKEN,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET,
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            wait_on_rate_limit=True
        )
        lg.info("X client initialized successfully")
        return x_client
    except Exception as e:
        lg.error(f"Failed to initialize X client: {e}")
        return None

# Perform crypto update
async def perform_coin_update(x_client, session, post_to_x=True):
    """Fetch coin data, news, YouTube videos, and post updates to X and Discord."""
    try:
        # Get top coins from the database
        top_coins = db_manager.get_top_coins()
        coin_ids = [coin['id'] for coin in top_coins]
        lg.info(f"Getting top coins from {db_manager.db_path}: {coin_ids}")

        # Fetch coin data
        coins_data = await fetch_all_data(coin_ids, session)
        if not coins_data:
            lg.error("No coin data fetched")
            return False

        # Fetch news
        news_dict = await fetch_news(coin_ids, session)
        if not news_dict:
            lg.warning("No news data fetched")

        # Fetch YouTube videos
        youtube_videos = await fetch_youtube_videos(['crypto market update'])
        if not youtube_videos:
            lg.warning("No YouTube videos fetched")

        # Fetch on-chain metrics
        santiment_metrics = await fetch_santiment_metrics(coin_ids, session)
        if not santiment_metrics:
            lg.warning("No Santiment metrics fetched")

        # Create thread content
        posts = create_thread_content(coins_data, news_dict, youtube_videos, santiment_metrics)

        # Post to X if enabled
        if post_to_x and x_client:
            await post_x_thread(x_client, posts)
            lg.info("Successfully posted X thread")

        # Post to Discord
        channel = bot.get_channel(int(DISCORD_CHANNEL_ID))
        if channel:
            await post_discord_update(channel, coins_data, news_dict, youtube_videos)
            lg.info("Successfully posted Discord update")
        else:
            lg.error(f"Discord channel {DISCORD_CHANNEL_ID} not found")

        return True

    except Exception as e:
        lg.error(f"Error in perform_coin_update: {e}")
        return False

# Schedule updates
async def schedule_updates(x_client):
    """Schedule periodic updates for X and Discord."""
    lg.info("Starting schedule_updates loop")

    async with aiohttp.ClientSession() as session:
        while True:
            now = datetime.now(timezone.utc)

            # Define thread types and their intervals (in hours)
            threads = [
                {"type": "Coin Update", "interval": 2},
                {"type": "News Update", "interval": 4},
                {"type": "Analytics Update", "interval": 6}
            ]

            next_run = None
            scheduler = None
            for thread in threads:
                # For simplicity, we'll just run the coin update for now
                if thread["type"] == "Coin Update":
                    # Set up the schedule
                    scheduler = schedule.every(thread["interval"]).hours.at(":44").do(lambda: None)
                    # Get the next run time
                    next_run = scheduler.next_run
                    # Ensure next_run is timezone-aware (same as 'now')
                    if next_run.tzinfo is None:
                        next_run = pytz.UTC.localize(next_run)
                    break

            if next_run is None:
                lg.error("No schedule defined for updates")
                return

            # Calculate the time difference
            sleep_seconds = (next_run - now).total_seconds()
            if sleep_seconds < 0:
                # If next_run is in the past, wait until the next occurrence
                lg.warning(f"Next run time {next_run} is in the past. Rescheduling...")
                schedule.run_all()  # Trigger the scheduler to update next_run
                next_run = scheduler.next_run
                if next_run.tzinfo is None:
                    next_run = pytz.UTC.localize(next_run)
                sleep_seconds = (next_run - now).total_seconds()

            lg.info(f"Sleeping for {sleep_seconds:.2f} seconds until {next_run} to post X update")
            await asyncio.sleep(sleep_seconds)

            # Perform the update
            lg.info("Performing scheduled crypto update")
            success = await perform_coin_update(x_client, session)
            if success:
                lg.info("Scheduled update completed successfully")
            else:
                lg.error("Scheduled update failed")

# Discord command to manually trigger an update
@bot.command()
async def update(ctx):
    lg.info(f'Received !update command from {ctx.author}')
    async with aiohttp.ClientSession() as session:
        success = await perform_coin_update(initialize_x_client(), session, post_to_x=False)
        if success:
            await ctx.send("Crypto update posted to Discord!")
        else:
            await ctx.send("Failed to post crypto update.")

# On ready event
@bot.event
async def on_ready():
    lg.info(f"Shard ID {bot.shard_id} has connected to Gateway (Session ID: {bot.ws.session_id}).")
    lg.info(f"Bot logged in as {bot.user.name}#{bot.user.discriminator}")
    x_client = initialize_x_client()
    channel = bot.get_channel(int(os.getenv('DISCORD_CHANNEL_ID')))
    await channel.send("Bot is now online!")

    # Run follow_crypto_users in a separate thread
    loop = asyncio.get_running_loop()
    def sync_follow():
        # Create a new event loop to run the async follow_crypto_users
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            new_loop.run_until_complete(follow_crypto_users(x_client))
        finally:
            new_loop.close()
    await loop.run_in_executor(None, sync_follow)

    await schedule_updates(x_client)

# Main entry point
if __name__ == "__main__":
    lg.info("Starting Crypto Market Update Bot")
    lg.info("Starting Discord bot")
    bot.run(DISCORD_TOKEN)