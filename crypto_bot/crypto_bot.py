import time
import logging
from datetime import datetime, timezone, timedelta
import schedule
import sqlite3
from requests.exceptions import HTTPError
import tweepy
import requests
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crypto_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API and X credentials (loaded from environment variables)
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/markets"
X_API_KEY = os.getenv("X_API_KEY", "your_x_api_key")
X_API_SECRET = os.getenv("X_API_SECRET", "your_x_api_secret")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "your_x_access_token")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "your_x_access_token_secret")

# Check if credentials are set
if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
    raise ValueError(
        "Missing X API credentials. Set X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, and X_ACCESS_TOKEN_SECRET as environment variables.")

# Database path
DB_PATH = r"c:\CryptoBot\crypto_bot\data\crypto_bot.db"

# File to track monthly post count
POST_COUNT_FILE = r"c:\CryptoBot\crypto_bot\data\post_count.txt"
X_FREE_TIER_POST_LIMIT = 500  # Free tier limit: 500 posts per month


def load_post_count():
    """Load the current post count and last reset date from a file."""
    if not os.path.exists(POST_COUNT_FILE):
        return 0, datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    try:
        with open(POST_COUNT_FILE, 'r') as f:
            count, last_reset = f.read().strip().split(',')
            return int(count), datetime.strptime(last_reset, "%Y-%m-%d %H:%M:%S%z")
    except Exception as e:
        logger.error(f"Error loading post count: {e}")
        return 0, datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def save_post_count(count, last_reset):
    """Save the post count and last reset date to a file."""
    try:
        with open(POST_COUNT_FILE, 'w') as f:
            f.write(f"{count},{last_reset.strftime('%Y-%m-%d %H:%M:%S%z')}")
    except Exception as e:
        logger.error(f"Error saving post count: {e}")


def check_post_limit():
    """Check if the monthly post limit has been reached, reset if necessary."""
    current_time = datetime.now(timezone.utc)
    post_count, last_reset = load_post_count()

    # Reset the count if it's a new month
    current_month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if last_reset < current_month_start:
        logger.info("New month detected, resetting post count.")
        post_count = 0
        last_reset = current_month_start
        save_post_count(post_count, last_reset)

    return post_count, last_reset


def increment_post_count(posts_made, last_reset):
    """Increment the post count after a successful post."""
    post_count, _ = load_post_count()
    post_count += posts_made
    save_post_count(post_count, last_reset)
    return post_count


def get_top_coins(db_path):
    """Fetch the list of top coins from the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT coin_id FROM top_coins")
        coins = [row[0] for row in cursor.fetchall()]
        conn.close()
        logger.info(f"Retrieved top coins from database: {coins}")
        return coins
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return []


def fetch_coin_data(coin_ids, retries=5, initial_delay=1):
    """Fetch coin data from CoinGecko API with rate-limit handling."""
    params = {
        "vs_currency": "usd",
        "ids": ",".join(coin_ids),
        "order": "market_cap_desc",
        "per_page": len(coin_ids),
        "page": 1,
        "sparkline": False
    }
    delay = initial_delay
    for attempt in range(retries):
        try:
            response = requests.get(COINGECKO_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched data for coins: {coin_ids}")
            return data
        except HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Rate limit hit (HTTP 429), retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error(f"API error: {e}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching coin data: {e}")
            return None
    logger.error("Max retries reached for fetching coin data.")
    return None


def post_to_x(coin_data):
    """Post the crypto update to X."""
    try:
        # Check post limit before proceeding
        post_count, last_reset = check_post_limit()
        posts_to_make = 1 + len(coin_data) + 1  # Main tweet + replies + engagement tweet
        if post_count + posts_to_make > X_FREE_TIER_POST_LIMIT:
            logger.warning(
                f"Cannot post: Monthly post limit ({X_FREE_TIER_POST_LIMIT}) reached. Current count: {post_count}")
            return False

        # Authenticate with X
        client = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )

        # Create the main post
        main_post = "🚀 Crypto Market Update ({})! 📈 Latest on top altcoins: {}\n#Crypto #Altcoins".format(
            datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            ", ".join([coin["id"].capitalize() for coin in coin_data])
        )
        main_tweet = client.create_tweet(text=main_post)
        main_tweet_id = main_tweet.data["id"]
        logger.info(f"Posted main tweet: {main_post}")

        # Reply with details for each coin
        previous_tweet_id = main_tweet_id
        for coin in coin_data:
            coin_text = (
                f"{coin['id']} ({coin['symbol'].upper()}): ${coin['current_price']:.2f} "
                f"({coin['price_change_percentage_24h']:.2f}% 24h) 📈\n"
                f"Market Cap: ${coin['market_cap']:,}\n"
                f"Top Project: N/A\n"
                f"#{coin['id'].upper()}"
            )
            reply_tweet = client.create_tweet(
                text=coin_text,
                in_reply_to_tweet_id=previous_tweet_id
            )
            previous_tweet_id = reply_tweet.data["id"]
            logger.info(f"Posted reply for {coin['id']}: {coin_text}")

        # Add an engagement post
        engagement_text = "Which altcoin are you most excited about today? 🚀 Drop your thoughts below! 👇 #Crypto #Altcoins"
        client.create_tweet(
            text=engagement_text,
            in_reply_to_tweet_id=previous_tweet_id
        )
        logger.info("Posted engagement tweet.")

        # Increment post count
        post_count = increment_post_count(posts_to_make, last_reset)
        logger.info(f"Updated post count: {post_count}/{X_FREE_TIER_POST_LIMIT}")
        return True

    except tweepy.TweepyException as e:
        logger.error(f"Error posting to X: {e}, Response: {e.response.text if e.response else 'No response'}")
        return False


def perform_crypto_update():
    """Perform a scheduled crypto update."""
    logger.info("Performing scheduled crypto update")
    # Step 1: Get top coins
    coin_ids = get_top_coins(DB_PATH)
    if not coin_ids:
        logger.error("No coins retrieved from database, aborting update.")
        return

    # Step 2: Fetch coin data
    coin_data = fetch_coin_data(coin_ids)
    if not coin_data:
        logger.warning("No coin data fetched, update failed.")
        return

    # Step 3: Post to X
    if post_to_x(coin_data):
        logger.info("Crypto update posted successfully.")
    else:
        logger.warning("Crypto update posting skipped or failed.")


# Scheduling logic
def schedule_updates():
    """Schedule crypto updates to run periodically."""
    # Run once per day at 00:40 UTC (matches Currency Gator post time)
    schedule.every().day.at("00:40").do(perform_crypto_update)

    # Initial run if needed
    perform_crypto_update()

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute to avoid tight loops


if __name__ == "__main__":
    try:
        logger.info("Starting CryptoBot...")
        schedule_updates()
    except KeyboardInterrupt:
        logger.info("CryptoBot stopped by user.")
    except Exception as e:
        logger.critical(f"Unexpected error in CryptoBot: {e}")