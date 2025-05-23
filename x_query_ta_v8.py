import discord
from discord.ext import commands
from dotenv import load_dotenv
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import os
from datetime import datetime, UTC, timedelta
import asyncio
import aiohttp
import pandas as pd
from sklearn.linear_model import LinearRegression
from joblib import dump
from googleapiclient.discovery import build
import random
import traceback
import json
import hashlib
import tweepy
from tweepy import TooManyRequests
import time
import logging
import sqlite3
from contextlib import contextmanager
import uuid

# Setup logging with custom formatter to suppress repetitive warnings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress repetitive warnings for specific modules
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('googleapiclient').setLevel(logging.WARNING)

# Rate limit tracking
COINGECKO_REQUESTS = 0
COINGECKO_RATE_LIMIT = 8
COINGECKO_RESET_TIME = time.time()
COINGECKO_MAX_RETRIES = 5

def format_number(value):
    try:
        value = float(value.replace('$', '').replace(',', ''))
        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        elif value >= 1_000:
            return f"${value / 1_000:.2f}K"
        else:
            return f"${value:,.2f}"
    except (ValueError, AttributeError):
        return "N/A"

async def download_vader_lexicon(max_retries=5, delay=10):
    try:
        if nltk.data.find('sentiment/vader_lexicon'):
            logger.info("VADER lexicon available.")
            return True
    except LookupError:
        logger.info("VADER lexicon not found. Attempting to download...")
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head("https://www.google.com", timeout=5) as response:
                    if response.status == 200:
                        nltk.download('vader_lexicon', quiet=True)
                        logger.info("VADER lexicon downloaded successfully.")
                        return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"No network connectivity (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
            else:
                logger.error("Max retries reached. Skipping VADER lexicon download.")
                return False
    return False

# Initialize environment and bot
load_dotenv()
logger.info(f"DISCORD_TOKEN: {'Set' if os.getenv('DISCORD_TOKEN') else 'Not set'}")
logger.info(f"YOUTUBE_API_KEY: {'Set' if os.getenv('YOUTUBE_API_KEY') else 'Not set'}")
logger.info(f"NEWSAPI_KEY: {'Set' if os.getenv('NEWSAPI_KEY') else 'Not set'}")
logger.info(f"DAPPRADAR_API_KEY: {'Set' if os.getenv('DAPPRADAR_API_KEY') else 'Not set'}")
logger.info(f"X_API_KEY: {'Set' if os.getenv('X_API_KEY') else 'Not set'}")
logger.info(f"X_API_SECRET: {'Set' if os.getenv('X_API_SECRET') else 'Not set'}")
logger.info(f"X_ACCESS_TOKEN: {'Set' if os.getenv('X_ACCESS_TOKEN') else 'Not set'}")
logger.info(f"X_ACCESS_TOKEN_SECRET: {'Set' if os.getenv('X_ACCESS_TOKEN_SECRET') else 'Not set'}")

if not os.getenv("DISCORD_TOKEN"):
    logger.error("DISCORD_TOKEN is not set in .env file. Exiting.")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize APIs
youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))

# Validate X API credentials
x_api_keys = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
for key in x_api_keys:
    if not os.getenv(key):
        logger.error(f"{key} is not set in .env file. X posting will fail.")
        exit(1)

try:
    x_client = tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
    )
    x_api = tweepy.API(
        tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"),
            os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"),
            os.getenv("X_ACCESS_TOKEN_SECRET")
        )
    )
    x_api.verify_credentials()
    logger.info("X API credentials verified successfully.")
except tweepy.TweepyException as e:
    logger.error(f"Failed to verify X API credentials: {e}. Check .env file and ensure keys are valid.")
    exit(1)

# Initialize VADER sentiment analyzer
sid = None
if asyncio.run(download_vader_lexicon()):
    sid = SentimentIntensityAnalyzer()

# Configuration
USE_TOP_ACCOUNTS = True
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE = os.path.join(DATA_DIR, "crypto_bot.db")

# SQLite database setup
def init_database():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thread_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                post_hashes TEXT NOT NULL,
                influencers TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coin_data_cache (
                coin_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                last_updated REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_cache (
                query TEXT PRIMARY KEY,
                result TEXT NOT NULL,
                date TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS youtube_cache (
                query TEXT PRIMARY KEY,
                result TEXT NOT NULL,
                last_updated REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS youtube_summary_cache (
                query TEXT PRIMARY KEY,
                result TEXT NOT NULL,
                last_updated REAL NOT NULL
            )
        """)
        conn.commit()

def clean_news_cache():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT query, result FROM news_cache")
        for row in cursor.fetchall():
            query, result = row
            try:
                json.loads(result)
            except json.JSONDecodeError as e:
                logger.warning(f"Removing corrupted news_cache entry for query {query}: {e}")
                cursor.execute("DELETE FROM news_cache WHERE query = ?", (query,))
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    try:
        yield conn
    finally:
        conn.close()

init_database()
clean_news_cache()

# Coin data
coin_names = {
    'ripple': 'Ripple',
    'hedera-hashgraph': 'Hedera Hashgraph',
    'stellar': 'Stellar',
    'xdce-crowd-sale': 'XDC',
    'sui': 'Sui',
    'ondo': 'Ondo',
    'algorand': 'Algorand',
    'cspr': 'Casper'
}

coin_symbols = {
    'ripple': 'XRPUSD',
    'hedera-hashgraph': 'HBARUSD',
    'stellar': 'XLMUSD',
    'xdce-crowd-sale': 'XDCUSD',
    'sui': 'SUIUSD',
    'ondo': 'ONDOUSD',
    'algorand': 'ALGOUSD',
    'cspr': 'CSPRUSD'
}

token_symbols = {
    'ripple': 'XRP',
    'hedera-hashgraph': 'HBAR',
    'stellar': 'XLM',
    'xdce-crowd-sale': 'XDC',
    'sui': 'SUI',
    'ondo': 'ONDO',
    'algorand': 'ALGO',
    'cspr': 'CSPR'
}

exchange_links = {
    'ripple': 'https://uphold.com/en/assets/xrp',
    'hedera-hashgraph': 'https://uphold.com/en/assets/hbar',
    'stellar': 'https://www.coinbase.com/price/stellar-lumens',
    'xdce-crowd-sale': 'https://uphold.com/en/assets/xdc',
    'sui': 'https://www.coinbase.com/price/sui',
    'ondo': 'https://www.coinbase.com/price/ondo',
    'algorand': 'https://www.coinbase.com/price/algorand',
    'cspr': 'https://www.kraken.com/prices/casper'
}

project_sources = {
    'ripple': {'count': 50, 'source': 'RippleX', 'url': 'https://ripplex.io/', 'partnerships': 20, 'total_projects': 150},
    'hedera-hashgraph': {'count': 100, 'source': 'Hedera.com', 'url': 'https://hedera.com/ecosystem', 'partnerships': 30, 'total_projects': 200},
    'stellar': {'count': 200, 'source': 'Stellar.org', 'url': 'https://www.stellar.org/ecosystem/projects', 'partnerships': 25, 'total_projects': 250},
    'xdce-crowd-sale': {'count': 50, 'source': 'XinFin.org', 'url': 'https://xinfin.org/ecosystem', 'partnerships': 15, 'total_projects': 100},
    'sui': {'count': 150, 'source': 'Sui.io', 'url': 'https://sui.io/ecosystem', 'partnerships': 20, 'total_projects': 300},
    'ondo': {'count': 80, 'source': 'Ondo.finance', 'url': 'https://ondo.finance/ecosystem', 'partnerships': 10, 'total_projects': 120},
    'algorand': {'count': 200, 'source': 'Algorand.com', 'url': 'https://algorand.com/ecosystem', 'partnerships': 30, 'total_projects': 350},
    'cspr': {'count': 100, 'source': 'Casper.network', 'url': 'https://casper.network/ecosystem', 'partnerships': 15, 'total_projects': 200}
}

daily_projects = {
    'ripple': [
        ("Sologenic", "Tokenizes assets like stocks on XRPL", "https://sologenic.org"),
        ("XRPL Labs", "Building Xumm wallet for XRPL", "https://xrpl-labs.com")
    ],
    'hedera-hashgraph': [
        ("SaucerSwap", "DeFi DEX on Hedera", "https://saucerswap.finance"),
        ("Hashport", "Cross-chain bridge for Hedera", "https://hashport.network")
    ],
    'stellar': [
        ("StellarAid", "Charity payments on Stellar", "https://stellaraid.org"),
        ("Vibrant", "Mobile wallet for Stellar", "https://vibrant.io")
    ],
    'xdce-crowd-sale': [
        ("TradeFinex", "Trade finance on XDC", "https://tradefinex.org"),
        ("XDC Network", "Hybrid blockchain solutions", "https://xdc.network")
    ],
    'sui': [
        ("Cetus", "DeFi protocol on Sui", "https://cetus.zone"),
        ("Navi Protocol", "Lending protocol on Sui", "https://naviprotocol.io")
    ],
    'ondo': [
        ("Ondo Vaults", "Structured finance on Ondo", "https://ondo.finance/vaults"),
        ("Flux", "Tokenized assets on Ondo", "https://ondo.finance/flux")
    ],
    'algorand': [
        ("Algofi", "DeFi lending on Algorand", "https://algofi.org"),
        ("Folks Finance", "Lending and borrowing on Algorand", "https://folks.finance")
    ],
    'cspr': [
        ("CasperPad", "Launchpad on Casper", "https://www.coingecko.com/en/coins/casperpad"),
        ("CasperLabs", "Enterprise blockchain solutions", "https://casperlabs.io")
    ]
}

influencers = {
    'XRP': [
        {'handle': '@Ripple', 'followers': 2000000, 'engagement': 5, 'accuracy': 5, 'trend_score': 4, 'reason': 'Official Ripple account'},
        {'handle': '@XRPcryptowolf', 'followers': 500000, 'engagement': 4, 'accuracy': 4, 'trend_score': 3, 'reason': 'Active in XRP discussions'},
        {'handle': '@JoelKatz', 'followers': 300000, 'engagement': 3, 'accuracy': 4, 'trend_score': 2, 'reason': 'Ripple CTO, technical insights'}
    ],
    'HBAR': [
        {'handle': '@Hedera', 'followers': 350000, 'engagement': 4, 'accuracy': 5, 'trend_score': 4, 'reason': 'Official Hedera account'},
        {'handle': '@LeemonBaird', 'followers': 150000, 'engagement': 3, 'accuracy': 4, 'trend_score': 3, 'reason': 'Hedera co-founder'},
        {'handle': '@HederaToday', 'followers': 100000, 'engagement': 3, 'accuracy': 3, 'trend_score': 2, 'reason': 'Hedera news updates'}
    ],
    'XLM': [
        {'handle': '@StellarOrg', 'followers': 750000, 'engagement': 4, 'accuracy': 5, 'trend_score': 4, 'reason': 'Official Stellar account'},
        {'handle': '@JedMcCaleb', 'followers': 200000, 'engagement': 3, 'accuracy': 4, 'trend_score': 3, 'reason': 'Stellar co-founder'},
        {'handle': '@XLMcommunity', 'followers': 150000, 'engagement': 3, 'accuracy': 3, 'trend_score': 2, 'reason': 'Stellar community updates'}
    ],
    'XDC': [
        {'handle': '@XinFin_Official', 'followers': 120000, 'engagement': 4, 'accuracy': 5, 'trend_score': 4, 'reason': 'Official XDC account'},
        {'handle': '@XDCFoundation', 'followers': 80000, 'engagement': 3, 'accuracy': 4, 'trend_score': 3, 'reason': 'XDC ecosystem updates'},
        {'handle': '@XDC_Network', 'followers': 60000, 'engagement': 3, 'accuracy': 3, 'trend_score': 2, 'reason': 'XDC network news'}
    ],
    'SUI': [
        {'handle': '@SuiNetwork', 'followers': 250000, 'engagement': 4, 'accuracy': 5, 'trend_score': 4, 'reason': 'Official Sui account'},
        {'handle': '@SuiGlobal', 'followers': 150000, 'engagement': 3, 'accuracy': 4, 'trend_score': 3, 'reason': 'Sui global updates'},
        {'handle': '@Mysten_Labs', 'followers': 100000, 'engagement': 3, 'accuracy': 3, 'trend_score': 2, 'reason': 'Sui developer team'}
    ],
    'ONDO': [
        {'handle': '@OndoFinance', 'followers': 100000, 'engagement': 4, 'accuracy': 5, 'trend_score': 4, 'reason': 'Official Ondo account'},
        {'handle': '@OndoProtocol', 'followers': 80000, 'engagement': 3, 'accuracy': 4, 'trend_score': 3, 'reason': 'Ondo protocol updates'},
        {'handle': '@OndoCommunity', 'followers': 60000, 'engagement': 3, 'accuracy': 3, 'trend_score': 2, 'reason': 'Ondo community insights'}
    ],
    'ALGO': [
        {'handle': '@Algorand', 'followers': 300000, 'engagement': 4, 'accuracy': 5, 'trend_score': 4, 'reason': 'Official Algorand account'},
        {'handle': '@AlgoFoundation', 'followers': 200000, 'engagement': 3, 'accuracy': 4, 'trend_score': 3, 'reason': 'Algorand ecosystem news'},
        {'handle': '@AlgorandDev', 'followers': 150000, 'engagement': 3, 'accuracy': 3, 'trend_score': 2, 'reason': 'Algorand developer updates'}
    ],
    'CSPR': [
        {'handle': '@Casper_Network', 'followers': 150000, 'engagement': 4, 'accuracy': 5, 'trend_score': 4, 'reason': 'Official Casper account'},
        {'handle': '@CasperLabs', 'followers': 100000, 'engagement': 3, 'accuracy': 4, 'trend_score': 3, 'reason': 'Casper enterprise solutions'},
        {'handle': '@CSPR_Live', 'followers': 80000, 'engagement': 3, 'accuracy': 3, 'trend_score': 2, 'reason': 'Casper network updates'}
    ]
}

channel_ids = [
    ("UCvMhY91Q8Z7x6yM91W-vsaA", "@CoinBureau"),
    ("UCqK_GSMbpiV8spgD3ZGloSw", "@Bankless"),
    ("UCZJUrYVH6lZcH88QXue-WkQ", "@WhiteboardCrypto"),
    ("UCtQycmSrKdJ0zE0bWumO4vA", "@digitalassetinvestor")
]

prior_year_averages = {
    'ripple': 0.60,
    'hedera-hashgraph': 0.09,
    'stellar': 0.11,
    'xdce-crowd-sale': 0.03,
    'sui': 0.80,
    'ondo': 0.25,
    'algorand': 0.15,
    'cspr': 0.04
}

async def test_url(url, session, timeout=5):
    try:
        async with session.head(url, timeout=timeout, allow_redirects=True) as response:
            if response.status == 200:
                logger.debug(f"URL {url} is functional (status: {response.status})")
                return True, url
        async with session.get(url, timeout=timeout, allow_redirects=True) as response:
            if response.status == 200:
                logger.debug(f"URL {url} is functional via GET (status: {response.status})")
                return True, url
        logger.warning(f"URL {url} returned non-200 status: {response.status}")
        return False, "https://www.coinbase.com"
    except Exception as e:
        logger.error(f"Error testing URL {url}: {type(e).__name__} - {str(e)}")
        return False, "https://www.coinbase.com"

async def get_top_coins():
    global COINGECKO_REQUESTS, COINGECKO_RESET_TIME
    supported_coins = list(coin_names.keys())
    async with aiohttp.ClientSession() as session:
        valid_coins = []
        for attempt in range(COINGECKO_MAX_RETRIES):
            try:
                current_time = time.time()
                if current_time - COINGECKO_RESET_TIME > 60:
                    COINGECKO_REQUESTS = 0
                    COINGECKO_RESET_TIME = current_time
                if COINGECKO_REQUESTS >= COINGECKO_RATE_LIMIT:
                    wait_time = 60 - (current_time - COINGECKO_RESET_TIME)
                    if wait_time > 0:
                        logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds...")
                        await asyncio.sleep(wait_time)
                    COINGECKO_REQUESTS = 0
                    COINGECKO_RESET_TIME = current_time
                COINGECKO_REQUESTS += 1

                async with session.get(
                        "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1",
                        timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    data = await response.json()
                    if not isinstance(data, list) or not data:
                        logger.error(f"Invalid CoinGecko response: {data}")
                        raise ValueError("Empty or invalid response from CoinGecko")
                    valid_coins = [coin["id"] for coin in data if coin["id"] in supported_coins]
                    logger.info(f"CoinGecko returned {len(data)} coins, filtered to {len(valid_coins)} supported coins: {valid_coins}")

                    # Validate all supported coins
                    for coin in supported_coins:
                        if coin not in valid_coins:
                            # Check if coin has cached data
                            with get_db() as conn:
                                cursor = conn.cursor()
                                cursor.execute("SELECT data, last_updated FROM coin_data_cache WHERE coin_id = ?", (coin,))
                                row = cursor.fetchone()
                                if row and (datetime.now(UTC).timestamp() - row[1]) < 3600:
                                    valid_coins.append(coin)
                                    logger.debug(f"Added {coin} to valid_coins based on cached data")
                                else:
                                    logger.warning(f"Coin {coin} not found in CoinGecko markets and no recent cache, may use fallback data")

                    coins = valid_coins[:4]
                    if len(coins) < 4:
                        logger.warning(f"Insufficient valid coins from CoinGecko ({len(coins)}), supplementing with supported coins.")
                        needed = 4 - len(coins)
                        history = load_history()
                        recent_coins = set()
                        for entry in history[-1:]:
                            for post in json.loads(entry['post_hashes']):
                                for coin in supported_coins:
                                    if coin_names[coin] in post:
                                        recent_coins.add(coin)
                        available_coins = [c for c in supported_coins if c not in coins and c not in recent_coins]
                        additional_coins = random.sample(available_coins, min(needed, len(available_coins)))
                        if len(additional_coins) < needed:
                            remaining = needed - len(additional_coins)
                            additional_coins.extend(random.sample([c for c in supported_coins if c not in coins and c not in additional_coins], remaining))
                        coins.extend(additional_coins)
                        logger.info(f"Supplemented with {additional_coins}")
                    logger.info(f"Final coins list: {coins}")
                    return coins
            except Exception as e:
                logger.error(f"Error fetching top coins (attempt {attempt + 1}/{COINGECKO_MAX_RETRIES}): {type(e).__name__}: {str(e)}")
                if attempt < COINGECKO_MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt * 15)
                else:
                    logger.warning("Max retries reached, returning fallback coins.")
                    return random.sample(supported_coins, 4)
    return random.sample(supported_coins, 4)

def load_history():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, post_hashes, influencers FROM thread_history")
        history = []
        for row in cursor.fetchall():
            try:
                history.append({
                    "timestamp": row[0],
                    "post_hashes": json.loads(row[1]),
                    "influencers": json.loads(row[2]) if row[2] else []
                })
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing thread_history JSON for row {row}: {e}")
                continue
    return history

def save_history(history):
    with get_db() as conn:
        cursor = conn.cursor()
        for entry in history:
            try:
                cursor.execute(
                    "INSERT OR REPLACE INTO thread_history (timestamp, post_hashes, influencers) VALUES (?, ?, ?)",
                    (entry["timestamp"], json.dumps(entry["post_hashes"]), json.dumps(entry.get("influencers", [])))
                )
            except Exception as e:
                logger.error(f"Error saving history entry {entry}: {e}")
                continue
        conn.commit()

def prune_history(history):
    cutoff = (datetime.now(UTC) - timedelta(days=2)).timestamp()
    return [entry for entry in history if entry['timestamp'] > cutoff]

def hash_post(post):
    return hashlib.md5(post.encode()).hexdigest()

def is_thread_unique(thread, history):
    thread_hashes = [hash_post(post) for post in thread]
    duplicate_count = 0
    duplicate_posts = []
    for post, post_hash in zip(thread, thread_hashes):
        for entry in history:
            if post_hash in entry['post_hashes']:
                logger.debug(f"Duplicate post detected: hash {post_hash} found in history entry {entry['timestamp']}")
                duplicate_count += 1
                duplicate_posts.append(post[:50] + "..." if len(post) > 50 else post)
                break
    if duplicate_count > len(thread) / 2:
        logger.info(f"Skipping thread: {duplicate_count}/{len(thread)} posts are duplicates: {duplicate_posts}")
        return False
    logger.debug(f"Thread is unique: {duplicate_count}/{len(thread)} duplicate posts")
    return True

def get_used_influencers(history):
    used_influencers = set()
    cutoff = (datetime.now(UTC) - timedelta(days=2)).timestamp()
    for entry in history:
        if entry['timestamp'] > cutoff:
            for influencer in entry.get('influencers', []):
                used_influencers.add(influencer)
    return used_influencers

def score_influencers(influencer_list, followers):
    for influencer in influencer_list:
        # Scale to 100: 50% followers, 30% engagement, 10% accuracy, 10% trend_score
        follower_score = min(50.0, influencer['followers'] / 100000) * 0.5  # Max 25 for 5M followers
        engagement_score = influencer['engagement'] * 6.0  # Max 30 for engagement=5
        accuracy_score = influencer['accuracy'] * 2.0  # Max 10 for accuracy=5
        trend_score = influencer['trend_score'] * 2.0  # Max 10 for trend_score=5
        influencer['total_score'] = follower_score + engagement_score + accuracy_score + trend_score
    return sorted(influencer_list, key=lambda x: x['total_score'], reverse=True)

async def send_discord_message(channel_id, message, files=None):
    channel = bot.get_channel(channel_id)
    success = False
    if channel:
        for attempt in range(3):
            try:
                if len(message) > 2000:
                    message = message[:1997] + "..."
                if files:
                    discord_files = [discord.File(file) for file in files if file]
                    await channel.send(content=message, files=discord_files)
                else:
                    await channel.send(message)
                logger.info(f"Sent to Discord: {message[:100]}...")
                success = True
                break
            except discord.errors.HTTPException as e:
                if e.status == 429:
                    retry_after = e.retry_after if e.retry_after else 60
                    logger.warning(f"Discord rate limited. Retrying in {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                else:
                    logger.error(f"Discord error: {e}")
                    break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                break
    else:
        logger.error(f"Channel {channel_id} not found.")
    return success

async def send_x_thread(thread, chart_urls=None, influencers_per_post=None):
    parent_id = None
    for i, post in enumerate(thread):
        for attempt in range(3):
            try:
                if len(post) > 280:
                    post = post[:277] + "..."
                tweet = x_client.create_tweet(
                    text=post,
                    in_reply_to_tweet_id=parent_id if i > 0 else None
                )
                parent_id = tweet.data["id"]
                logger.info(f"Posted X Tweet {i + 1}: {tweet.data['id']}")
                await asyncio.sleep(5)
                break
            except TooManyRequests:
                logger.warning(f"X rate limit hit for tweet {i + 1}. Waiting 15 minutes...")
                await asyncio.sleep(900)
            except tweepy.TweepyException as e:
                logger.error(f"X error for tweet {i + 1}: {e}")
                if "401" in str(e):
                    logger.error("X API authentication failed. Check credentials in .env file.")
                if attempt < 2:
                    logger.info(f"Retrying tweet {i + 1} after 10 seconds...")
                    await asyncio.sleep(10)
                else:
                    logger.error(f"Failed to post tweet {i + 1} after 3 attempts.")
                    return False
            except Exception as e:
                logger.error(f"Unexpected X error for tweet {i + 1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(10)
                else:
                    return False
    return True

async def fetch_news(query):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT result, date FROM news_cache WHERE query = ?", (query,))
        row = cursor.fetchone()
        if row and datetime.fromisoformat(row[1]).date() == datetime.now(UTC).date():
            try:
                result = json.loads(row[0])
                logger.debug(f"Using cached news for {query}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing cached news for {query}: {e}")
                cursor.execute("DELETE FROM news_cache WHERE query = ?", (query,))
                conn.commit()

    newsapi_key = os.getenv('NEWSAPI_KEY')
    if not newsapi_key:
        logger.error("NEWSAPI_KEY not set in environment variables.")
        return {"headline": f"No news available for {query} (API key missing)", "url": ""}

    async def fetch_with_backoff(url, session, max_attempts=3):
        for attempt in range(max_attempts):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"NewsAPI rate limit hit for {query}, waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        continue
                    data = await response.json()
                    if not data:
                        logger.error(f"Empty response from NewsAPI for {query}")
                        return None
                    return data
            except Exception as e:
                logger.error(f"Error fetching news attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
        return None

    async with aiohttp.ClientSession() as session:
        url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&apiKey={newsapi_key}"
        data = await fetch_with_backoff(url, session)
        if not data or data.get("status") != "ok" or not data.get("articles"):
            logger.debug(f"No relevant news found for {query}")
            result = {"headline": f"No new updates for {query} today", "url": ""}
        else:
            article = data["articles"][0]
            headline = article.get("title", "No headline available")[:100]
            article_url = article.get("url", "")
            keywords = ["filed", "approved", "rejected", "settlement", "paused", "appeal", "ruling", "partnership", "launch", "update", "announce", "integrate", "collaborate"]
            if not any(keyword in headline.lower() for keyword in keywords):
                headline = article.get("title", f"No significant updates for {query} today")[:100]
                article_url = article.get("url", "") if article.get("url") else ""
            result = {"headline": headline, "url": article_url}

        with get_db() as conn:
            cursor = conn.cursor()
            if result and "headline" in result and "url" in result:
                try:
                    cursor.execute(
                        "INSERT OR REPLACE INTO news_cache (query, result, date) VALUES (?, ?, ?)",
                        (query, json.dumps(result), datetime.now(UTC).isoformat())
                    )
                    conn.commit()
                except Exception as e:
                    logger.error(f"Error caching news for {query}: {e}")
            else:
                logger.warning(f"Skipping cache for {query}: invalid result {result}")
        return result

async def get_youtube_summary():
    query = "crypto_market_summary"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT result, last_updated FROM youtube_summary_cache WHERE query = ?", (query,))
        row = cursor.fetchone()
        if row and (datetime.now(UTC).timestamp() - row[1]) < 3600:
            try:
                result = json.loads(row[0])
                logger.debug("Using cached YouTube summary")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing cached YouTube summary: {e}")
                cursor.execute("DELETE FROM youtube_summary_cache WHERE query = ?", (query,))
                conn.commit()

    summaries = []
    for channel_id, channel_name in channel_ids:
        try:
            channel_response = youtube.channels().list(
                part="contentDetails",
                id=channel_id
            ).execute()
            if "items" not in channel_response or not channel_response["items"]:
                summaries.append(f"{channel_name}: No channel found")
                continue
            uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            playlist_response = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=1
            ).execute()

            if "items" not in playlist_response or not playlist_response["items"]:
                summaries.append(f"{channel_name}: No videos found")
                continue
            video = playlist_response["items"][0]["snippet"]
            video_id = video["resourceId"]["videoId"]
            video_response = youtube.videos().list(
                part="snippet",
                id=video_id
            ).execute()
            description = video_response["items"][0]["snippet"]["description"] if video_response["items"] else ""
            summary = video["title"] if len(video["title"]) <= 60 else description.split('.')[0].strip()[:57] + "..."
            summaries.append(f"{channel_name}: {summary} youtu.be/{video_id}")
        except Exception as e:
            logger.error(f"Error fetching YouTube data for {channel_name}: {type(e).__name__}: {str(e)}")
            summaries.append(f"{channel_name}: Error fetching video")
        await asyncio.sleep(1)

    result = "\n".join(summaries)[:200] + ("..." if len("\n".join(summaries)) > 200 else "")
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO youtube_summary_cache (query, result, last_updated) VALUES (?, ?, ?)",
                (query, json.dumps(result), datetime.now(UTC).timestamp())
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Error caching YouTube summary: {e}")
    return result

async def fetch_youtube_content(query, session):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT result, last_updated FROM youtube_cache WHERE query = ?", (query,))
        row = cursor.fetchone()
        if row and (datetime.now(UTC).timestamp() - row[1]) < 3600:
            try:
                result = json.loads(row[0])
                logger.debug(f"Using cached YouTube data for {query}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing cached YouTube data for {query}: {e}")
                cursor.execute("DELETE FROM youtube_cache WHERE query = ?", (query,))
                conn.commit()

    try:
        search_response = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            order="date",
            maxResults=1,
            publishedAfter=(datetime.now(UTC) - timedelta(days=7)).isoformat()
        ).execute()

        videos = search_response.get("items", [])
        if videos:
            video = videos[0]["snippet"]
            video_id = videos[0]["id"]["videoId"]
            result = {
                "youtube": f"{video['channelTitle']}: {video['title']} (https://youtu.be/{video_id})",
                "youtube_score": 10 if "fundamental" in video["title"].lower() else 5
            }
        else:
            result = {"youtube": "No recent videos found", "youtube_score": 0}
    except Exception as e:
        logger.error(f"Error fetching YouTube for {query}: {type(e).__name__}: {str(e)}")
        result = {"youtube": f"Error: {e}", "youtube_score": 0}

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO youtube_cache (query, result, last_updated) VALUES (?, ?, ?)",
                (query, json.dumps(result), datetime.now(UTC).timestamp())
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Error caching YouTube data for {query}: {e}")
    return result

async def curate_content(coins, coin_names):
    content_data = {}
    async with aiohttp.ClientSession() as session:
        for coin in coins:
            if coin not in coin_names:
                logger.warning(f"Skipping unsupported coin: {coin}")
                content_data[coin] = {"youtube": "Unsupported coin", "youtube_score": 0, "x_accounts": "N/A"}
                continue
            try:
                youtube_data = await fetch_youtube_content(f"{coin_names[coin]} fundamentals", session)
                content_data[coin] = youtube_data
            except Exception as e:
                logger.error(f"Error curating YouTube for {coin}: {type(e).__name__}: {str(e)}")
                content_data[coin] = {"youtube": f"Error: {e}", "youtube_score": 0}

            scored_accounts = []
            token_key = token_symbols.get(coin, coin_names[coin].split()[0].upper())
            influencer_list = influencers.get(token_key, [])
            if influencer_list:
                scored_influencers = score_influencers(influencer_list, 0)
                for influencer in scored_influencers[:2]:
                    score = influencer['total_score']
                    reason = influencer['reason']
                    scored_accounts.append(f"{influencer['handle']} ({reason}, {score:.0f}/100)")
                content_data[coin]["x_accounts"] = ", ".join(scored_accounts) if scored_accounts else "No accounts curated"
            else:
                content_data[coin]["x_accounts"] = "No accounts curated"
            await asyncio.sleep(1)
    return content_data

async def get_top_accounts(coin, days=7):
    logger.debug(f"Fetching community data for {coin} (X API free-tier workaround)...")
    async with aiohttp.ClientSession() as session:
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin}?localization=false&tickers=false&market_data=false&community_data=true&developer_data=false&sparkline=false"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                data = await response.json()
                if not data:
                    logger.error(f"Empty response from CoinGecko for {coin}")
                    raise ValueError("Empty response")
                followers = data.get('community_data', {}).get('twitter_followers', 0)
                token_key = token_symbols.get(coin, coin_names[coin].split()[0].upper())
                top_influencers = influencers.get(token_key, [])[:3]
                accounts = [
                    {
                        "username": influencer["handle"],
                        "engagement": influencer["engagement"] * 100,
                        "text": f"Positive sentiment for {coin_names[coin]} based on {followers:,} Twitter followers!"
                    } for influencer in top_influencers
                ]
                logger.debug(f"Generated {len(accounts)} accounts for {coin} with {followers:,} followers")
                return accounts
        except Exception as e:
            logger.error(f"Error fetching community data for {coin}: {e}")
            return [
                {"username": f"@{coin}_user1", "engagement": random.randint(100, 1000), "text": f"Excited about {coin}!"},
                {"username": f"@{coin}_user2", "engagement": random.randint(50, 500), "text": f"{coin} is the future!"},
                {"username": f"@{coin}_user3", "engagement": random.randint(10, 200), "text": f"Checking {coin} charts"}
            ]

async def analyze_engagement(top_accounts, coin):
    analysis = []
    for account in top_accounts:
        text = account["text"]
        if sid:
            sentiment = sid.polarity_scores(text)["compound"]
            sentiment_label = "positive" if sentiment > 0.3 else "negative" if sentiment < -0.3 else "neutral"
        else:
            sentiment = 0.0
            sentiment_label = "neutral"
        has_media = "media" in text.lower() or "chart" in text.lower()
        has_news = any(keyword in text.lower() for keyword in ["sec", "etf", "partnership"])
        analysis.append({
            "username": account["username"],
            "engagement": account["engagement"],
            "sentiment": sentiment_label,
            "has_media": has_media,
            "has_news": has_news
        })
    with open(os.path.join(DATA_DIR, f"engagement_analysis_{coin}.txt"), "w") as f:
        f.write("\n".join([
                              f"{a['username']}: {a['engagement']} (Sentiment: {a['sentiment']}, Media: {a['has_media']}, News: {a['has_news']})"
                              for a in analysis]))
    return analysis

async def fetch_dapp_data(coin, session):
    chain_mapping = {
        'algorand': 'algorand',
        'sui': 'sui',
        'hedera-hashgraph': 'hedera',
    }
    chain = chain_mapping.get(coin.lower())
    if not chain:
        logger.debug(f"No DappRadar support for {coin}, using project_sources")
        projects = random.choice(daily_projects.get(coin, [])) if daily_projects.get(coin) else ("N/A", "No project data", "")
        return {
            'dapp_count': project_sources[coin]['total_projects'],
            'top_projects': [projects],
            'top_project_metrics': {'public_interest': 'N/A', 'corporate_utilization': f"{project_sources[coin]['partnerships']} partnerships"}
        }

    try:
        url = f"https://apis.dappradar.com/v2/dapps?chain={chain}&sort=transactions&order=desc&page=1&resultsPerPage=5"
        headers = {'X-Api-Key': os.getenv('DAPPRADAR_API_KEY')}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 429:
                logger.warning(f"DappRadar rate limit hit for {coin}, falling back to project_sources")
                projects = random.choice(daily_projects.get(coin, [])) if daily_projects.get(coin) else ("N/A", "No project data", "")
                return {
                    'dapp_count': project_sources[coin]['total_projects'],
                    'top_projects': [projects],
                    'top_project_metrics': {'public_interest': 'N/A', 'corporate_utilization': f"{project_sources[coin]['partnerships']} partnerships"}
                }
            data = await response.json()
            if not data.get('results'):
                logger.debug(f"No dApps found for {coin} on DappRadar, using project_sources")
                projects = random.choice(daily_projects.get(coin, [])) if daily_projects.get(coin) else ("N/A", "No project data", "")
                return {
                    'dapp_count': project_sources[coin]['total_projects'],
                    'top_projects': [projects],
                    'top_project_metrics': {'public_interest': 'N/A', 'corporate_utilization': f"{project_sources[coin]['partnerships']} partnerships"}
                }

            dapp_count = data.get('totalResults', project_sources[coin]['total_projects'])
            top_projects = [(dapp['name'], dapp['description'], dapp['website'] if dapp.get('website') else "") for dapp in data['results'][:1]]
            top_project_metrics = {
                'public_interest': f"{data['results'][0]['dailyUsers']} daily users" if data['results'] else 'N/A',
                'corporate_utilization': f"{project_sources[coin]['partnerships']} partnerships"
            }
            logger.info(f"Fetched {dapp_count} dApps for {coin} from DappRadar")
            return {
                'dapp_count': dapp_count,
                'top_projects': top_projects,
                'top_project_metrics': top_project_metrics
            }
    except Exception as e:
        logger.error(f"Error fetching DappRadar data for {coin}: {e}")
        projects = random.choice(daily_projects.get(coin, [])) if daily_projects.get(coin) else ("N/A", "No project data", "")
        return {
            'dapp_count': project_sources[coin]['total_projects'],
            'top_projects': [projects],
            'top_project_metrics': {'public_interest': 'N/A', 'corporate_utilization': f"{project_sources[coin]['partnerships']} partnerships"}
        }

async def fetch_historical_data(coin, session, days=14):
    historical_data = []
    end_date = datetime.now(UTC).date() - timedelta(days=1)
    start_date = end_date - timedelta(days=days)
    current_date = start_date
    missing_data_count = 0

    while current_date <= end_date:
        date_str = current_date.strftime("%d-%m-%Y")
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/history?date={date_str}&localization=false"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                data = await response.json()
                if not data:
                    logger.debug(f"Empty response for {coin} on {date_str}")
                    missing_data_count += 1
                    continue
                if 'market_data' in data:
                    historical_data.append({
                        'date': datetime.strptime(date_str, "%d-%m-%Y").timestamp(),
                        'price': data['market_data']['current_price']['usd'],
                        'volume': data['market_data']['total_volume']['usd'],
                        'market_cap': data['market_data']['market_cap']['usd']
                    })
                else:
                    logger.debug(f"No market data for {coin} on {date_str}")
                    missing_data_count += 1
        except Exception as e:
            logger.error(f"Error fetching historical data for {coin} on {date_str}: {e}")
            missing_data_count += 1
        current_date += timedelta(days=1)
        await asyncio.sleep(1)

    logger.info(f"Historical data for {coin}: {len(historical_data)} days fetched, {missing_data_count} days missing")
    return historical_data

def predict_price(historical_data, coin):
    if len(historical_data) < 3:
        logger.warning(f"Insufficient data for price prediction for {coin} ({len(historical_data)} days)")
        return None, "Insufficient data"

    df = pd.DataFrame(historical_data)
    required_columns = ['price', 'volume', 'market_cap']
    if not all(col in df for col in required_columns):
        logger.warning(f"Missing required columns in historical data for {coin}: {df.columns}")
        return None, "Missing data columns"

    df['price_lag1'] = df['price'].shift(1)
    df['price_lag2'] = df['price'].shift(2)
    df['volume_lag1'] = df['volume'].shift(1)
    df['market_cap_lag1'] = df['market_cap'].shift(1)
    df = df.dropna()

    if df.empty:
        logger.warning(f"No valid data after processing for {coin}")
        return None, "No valid data"

    X = df[['price_lag1', 'price_lag2', 'volume_lag1', 'market_cap_lag1']]
    y = df['price']

    model = LinearRegression()
    model.fit(X, y)

    latest = df.iloc[-1]
    next_day_features = pd.DataFrame([[
        latest['price'],
        latest['price_lag1'],
        latest['volume'],
        latest['market_cap']
    ]], columns=['price_lag1', 'price_lag2', 'volume_lag1', 'market_cap_lag1'])
    predicted_price = model.predict(next_day_features)[0]

    feature_names = ['price_lag1', 'price_lag2', 'volume_lag1', 'market_cap_lag1']
    coefficients = abs(model.coef_)
    max_feature_idx = coefficients.argmax()
    max_feature = feature_names[max_feature_idx]
    if max_feature in ['price_lag1', 'price_lag2']:
        explanation = "Price trend"
    elif max_feature == 'volume_lag1':
        explanation = "Volume surge"
    else:
        explanation = "Market cap shift"

    model_path = os.path.join(DATA_DIR, f"{coin}_price_model.joblib")
    dump(model, model_path)
    logger.info(f"Saved price prediction model for {coin} to {model_path}")

    return predicted_price, explanation

async def fetch_coin_data(coin, session):
    global COINGECKO_REQUESTS, COINGECKO_RESET_TIME
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT data, last_updated FROM coin_data_cache WHERE coin_id = ?", (coin,))
        row = cursor.fetchone()
        if row and (datetime.now(UTC).timestamp() - row[1]) < 3600:
            try:
                result = json.loads(row[0])
                logger.debug(f"Using cached coin data for {coin}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing cached coin data for {coin}: {e}")
                cursor.execute("DELETE FROM coin_data_cache WHERE coin_id = ?", (coin,))
                conn.commit()

    async def fetch_with_backoff(url, session, max_attempts=COINGECKO_MAX_RETRIES):
        global COINGECKO_REQUESTS, COINGECKO_RESET_TIME
        for attempt in range(max_attempts):
            try:
                current_time = time.time()
                if current_time - COINGECKO_RESET_TIME > 60:
                    COINGECKO_REQUESTS = 0
                    COINGECKO_RESET_TIME = current_time
                if COINGECKO_REQUESTS >= COINGECKO_RATE_LIMIT:
                    wait_time = 60 - (current_time - COINGECKO_RESET_TIME)
                    if wait_time > 0:
                        logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds...")
                        await asyncio.sleep(wait_time)
                    COINGECKO_REQUESTS = 0
                    COINGECKO_RESET_TIME = current_time
                COINGECKO_REQUESTS += 1
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 180))
                        logger.warning(f"CoinGecko rate limit hit for {url}, waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        continue
                    data = await response.json()
                    if not data or 'error' in data:
                        raise ValueError(f"Invalid response from {url}: {data.get('error', 'No data')}")
                    return data
            except Exception as e:
                logger.error(f"Error fetching {url} attempt {attempt + 1}: {type(e).__name__} - {str(e)}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** attempt * 15)
                else:
                    raise
        raise ValueError(f"Failed to fetch {url} after {max_attempts} attempts")

    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin}?localization=false&tickers=false&market_data=true&community_data=true&developer_data=true&sparkline=false"
        data = await fetch_with_backoff(url, session)
        content_data = await curate_content([coin], coin_names)
        historical_data = await fetch_historical_data(coin, session)
        predicted_price, prediction_explanation = predict_price(historical_data, coin) if historical_data else (None, "N/A")
        dapp_data = await fetch_dapp_data(coin, session)

        result = {
            "coin": coin_names[coin],
            "text": f"{coin_names[coin]}: ${data['market_data']['current_price']['usd']:.2f}",
            "full_text": f"{coin_names[coin]}: ${data['market_data']['current_price']['usd']:.2f} ({data['market_data']['price_change_percentage_24h']:.2f}% 24h)",
            "chart_url": f"https://www.tradingview.com/chart/?symbol=BITFINEX:{coin_symbols[coin]}",
            "market_cap": f"${data['market_data']['market_cap']['usd']:,}",
            "projects": project_sources[coin]["count"],
            "partnerships": project_sources[coin]["partnerships"],
            "project_source": project_sources[coin]["source"],
            "project_url": project_sources[coin]["url"],
            "total_projects": dapp_data['dapp_count'],
            "top_projects": dapp_data['top_projects'],
            "top_project_metrics": dapp_data['top_project_metrics'],
            "volume": data['market_data']['total_volume']['usd'],
            "exchange": exchange_links[coin],
            "price_change_24h": data['market_data']['price_change_percentage_24h'],
            "trend": "Bullish" if data['market_data']['price_change_percentage_24h'] > 0 else "Bearish",
            "ma_30": prior_year_averages.get(coin, 0),
            "prior_month_avg": prior_year_averages.get(coin, 0),
            "fundamentals": "N/A",
            "onchain_metrics": {
                "transaction_volume": f"${data['market_data']['total_volume']['usd']:,}",
                "active_addresses_proxy": f"{data.get('community_data', {}).get('twitter_followers', 0):,} Twitter followers",
                "tvl": "N/A",
                "developer_activity": f"{data.get('developer_data', {}).get('code_additions_deletions_4_weeks', 0)} code changes (4w)"
            },
            "curated_youtube": content_data.get(coin, {}).get("youtube", "N/A"),
            "curated_x": content_data.get(coin, {}).get("x_accounts", "N/A"),
            "twitter_followers": data.get('community_data', {}).get('twitter_followers', 0),
            "predicted_price": f"${predicted_price:.2f}" if predicted_price else "N/A",
            "prediction_explanation": prediction_explanation
        }
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT OR REPLACE INTO coin_data_cache (coin_id, data, last_updated) VALUES (?, ?, ?)",
                    (coin, json.dumps(result), datetime.now(UTC).timestamp())
                )
                conn.commit()
            except Exception as e:
                logger.error(f"Error caching coin data for {coin}: {e}")
        return result
    except Exception as e:
        logger.error(f"Failed to fetch data for {coin}: {e}")
        content_data = await curate_content([coin], coin_names)
        dapp_data = {
            'dapp_count': project_sources[coin]['total_projects'],
            'top_projects': [random.choice(daily_projects.get(coin, [("N/A", "No project data", "")]))],
            'top_project_metrics': {'public_interest': 'N/A', 'corporate_utilization': f"{project_sources[coin]['partnerships']} partnerships"}
        }
        return {
            "coin": coin_names[coin],
            "text": f"{coin_names[coin]}: Price unavailable",
            "full_text": f"{coin_names[coin]}: Data temporarily unavailable, check chart",
            "chart_url": f"https://www.tradingview.com/chart/?symbol=BITFINEX:{coin_symbols[coin]}",
            "market_cap": "N/A",
            "projects": project_sources[coin]["count"],
            "partnerships": project_sources[coin]["partnerships"],
            "project_source": project_sources[coin]["source"],
            "project_url": project_sources[coin]["url"],
            "total_projects": dapp_data['dapp_count'],
            "top_projects": dapp_data['top_projects'],
            "top_project_metrics": dapp_data['top_project_metrics'],
            "volume": 0,
            "exchange": exchange_links[coin],
            "price_change_24h": 0,
            "trend": "N/A",
            "ma_30": prior_year_averages.get(coin, 0),
            "prior_month_avg": prior_year_averages.get(coin, 0),
            "fundamentals": "N/A",
            "onchain_metrics": {
                "transaction_volume": "N/A",
                "active_addresses_proxy": "N/A",
                "tvl": "N/A",
                "developer_activity": "N/A"
            },
            "curated_youtube": content_data.get(coin, {}).get("youtube", "N/A"),
            "curated_x": content_data.get(coin, {}).get("x_accounts", "N/A"),
            "twitter_followers": 0,
            "predicted_price": "N/A",
            "prediction_explanation": "N/A"
        }

async def get_ta_data():
    ta_data = []
    coins = await get_top_coins()
    async with aiohttp.ClientSession() as session:
        logger.info(f"Fetching data for coins: {coins}")
        for coin in coins:
            try:
                data = await fetch_coin_data(coin, session)
                if not isinstance(data, dict):
                    raise ValueError(f"Invalid data type for {coin}: {type(data)}")
                ta_data.append(data)
            except Exception as e:
                logger.error(f"Failed to fetch data for {coin}: {e}")
                projects = random.choice(daily_projects.get(coin, [("N/A", "No project data", "")]))
                ta_data.append({
                    "coin": coin_names[coin],
                    "text": f"{coin_names[coin]}: Price unavailable",
                    "full_text": f"{coin_names[coin]}: Data temporarily unavailable, check chart",
                    "chart_url": f"https://www.tradingview.com/chart/?symbol=BITFINEX:{coin_symbols[coin]}",
                    "market_cap": "N/A",
                    "projects": project_sources[coin]["count"],
                    "partnerships": project_sources[coin]["partnerships"],
                    "project_source": project_sources[coin]["source"],
                    "project_url": project_sources[coin]["url"],
                    "total_projects": project_sources[coin]["total_projects"],
                    "top_projects": [projects],
                    "top_project_metrics": {'public_interest': 'N/A', 'corporate_utilization': f"{project_sources[coin]['partnerships']} partnerships"},
                    "volume": 0,
                    "exchange": exchange_links[coin],
                    "price_change_24h": 0,
                    "trend": "N/A",
                    "ma_30": prior_year_averages.get(coin, 0),
                    "prior_month_avg": prior_year_averages.get(coin, 0),
                    "fundamentals": "N/A",
                    "onchain_metrics": {
                        "transaction_volume": "N/A",
                        "active_addresses_proxy": "N/A",
                        "tvl": "N/A",
                        "developer_activity": "N/A"
                    },
                    "curated_youtube": "N/A",
                    "curated_x": "No accounts curated",
                    "twitter_followers": 0,
                    "predicted_price": "N/A",
                    "prediction_explanation": "N/A"
                })
            await asyncio.sleep(8)

    if len(ta_data) < len(coins):
        logger.warning(f"ta_data ({len(ta_data)}) shorter than coins ({len(coins)}), appending fallbacks...")
        for coin in coins[len(ta_data):]:
            projects = random.choice(daily_projects.get(coin, [("N/A", "No project data", "")]))
            ta_data.append({
                "coin": coin_names[coin],
                "text": f"{coin_names[coin]}: Price unavailable",
                "full_text": f"{coin_names[coin]}: Data temporarily unavailable, check chart",
                "chart_url": f"https://www.tradingview.com/chart/?symbol=BITFINEX:{coin_symbols[coin]}",
                "market_cap": "N/A",
                "projects": project_sources[coin]["count"],
                "partnerships": project_sources[coin]["partnerships"],
                "project_source": project_sources[coin]["source"],
                "project_url": project_sources[coin]["url"],
                "total_projects": project_sources[coin]["total_projects"],
                "top_projects": [projects],
                "top_project_metrics": {'public_interest': 'N/A', 'corporate_utilization': f"{project_sources[coin]['partnerships']} partnerships"},
                "volume": 0,
                "exchange": exchange_links[coin],
                "price_change_24h": 0,
                "trend": "N/A",
                "ma_30": prior_year_averages.get(coin, 0),
                "prior_month_avg": prior_year_averages.get(coin, 0),
                "fundamentals": "N/A",
                "onchain_metrics": {
                    "transaction_volume": "N/A",
                    "active_addresses_proxy": "N/A",
                    "tvl": "N/A",
                    "developer_activity": "N/A"
                },
                "curated_youtube": "N/A",
                "curated_x": "No accounts curated",
                "twitter_followers": 0,
                "predicted_price": "N/A",
                "prediction_explanation": "N/A"
            })

    logger.info(f"get_ta_data completed: {len(ta_data)} entries for coins {coins}")
    return ta_data

async def post_x_update():
    while True:
        try:
            coin_data = await get_ta_data()
            if not coin_data:
                logger.error("No coin data retrieved, skipping X update")
                await asyncio.sleep(14400)
                continue

            timestamp = datetime.now(UTC).strftime("%b %d, %Y")
            thread = [
                f"🚀 Crypto Market Update ({timestamp})! 📈 Latest on top altcoins: {', '.join([data['coin'] for data in coin_data[:4]])}. #Crypto #Altcoins"
            ]
            valid_coins = []

            for data in coin_data:
                try:
                    coin_id = [k for k, v in coin_names.items() if v == data['coin']][0]
                    news = await fetch_news(data['coin'])
                    top_project = data['top_projects'][0][0] if data['top_projects'] else "N/A"
                    project_url = data['top_projects'][0][2] if data['top_projects'] and data['top_projects'][0][2] and data['top_projects'][0][2] != "N/A" else ""
                    tx_volume = format_number(data['onchain_metrics']['transaction_volume'])
                    headline = news['headline'][:40] + "..." if len(news['headline']) > 40 else news['headline']
                    token_key = token_symbols.get(coin_id, data['coin'].split()[0].upper())
                    tweet_lines = [
                        f"{data['coin']} ({token_key}): ${data['text'].split('$')[1]} ({data['price_change_24h']:.2f}% 24h) {'📈' if data['price_change_24h'] > 0 else '📉'}",
                        f"Tx Volume: {tx_volume}",
                        f"Top Project: {top_project}" + (f" {project_url}" if project_url else ""),
                        f"News: {headline} {news['url']} #Crypto"
                    ]
                    if data['predicted_price'] != "N/A":
                        tweet_lines.insert(1, f"Predicted: {data['predicted_price']} ({data['prediction_explanation']})")
                    tweet = "\n".join(tweet_lines)
                    thread.append(tweet)
                    valid_coins.append(coin_id)
                except Exception as e:
                    logger.error(f"Error processing coin {data['coin']} for thread: {e}")
                    continue

            if len(thread) < 2:
                logger.error("Insufficient valid coin data for thread, skipping X update")
                await asyncio.sleep(14400)
                continue

            try:
                youtube_summary = await get_youtube_summary()
                if youtube_summary and youtube_summary.strip() != "":
                    thread.append(f"📹 Crypto Video Updates:\n{youtube_summary}\n#CryptoNews")
            except Exception as e:
                logger.error(f"Error fetching YouTube summary: {e}")
                thread.append(f"📹 Crypto Video Updates: Check channels like @CoinBureau for news! #CryptoNews")

            try:
                content_data = await curate_content(valid_coins, coin_names)
                influencers_list = []
                for coin in content_data:
                    if content_data[coin]['x_accounts'] != "No accounts curated":
                        influencers_list.extend(content_data[coin]['x_accounts'].split(", "))
                if influencers_list:
                    unique_influencers = []
                    seen_handles = set()
                    for influencer in influencers_list:
                        handle = influencer.split(" (")[0]
                        if handle not in seen_handles:
                            unique_influencers.append(influencer)
                            seen_handles.add(handle)
                    thread.append(
                        f"Stay tuned! Follow: {', '.join(unique_influencers[:3])}. #CryptoNews"
                    )
                else:
                    thread.append(f"Stay tuned for more crypto updates ({timestamp})! #CryptoNews")
            except Exception as e:
                logger.error(f"Error curating content for thread: {e}")
                thread.append(f"Stay tuned for more crypto updates ({timestamp})! #CryptoNews")

            history = load_history()
            thread_hashes = [hash_post(post) for post in thread]
            logger.debug(f"Thread content and hashes: {list(zip(thread, thread_hashes))}")
            if is_thread_unique(thread, history):
                success = await send_x_thread(thread)
                if success:
                    history.append({
                        "timestamp": datetime.now(UTC).timestamp(),
                        "post_hashes": thread_hashes,
                        "influencers": [infl.split(" (")[0] for infl in influencers_list]
                    })
                    save_history(prune_history(history))
                else:
                    logger.error("Failed to post thread to X, not saving to history")
            else:
                logger.info(f"Skipping X post: thread contains too many duplicates. Hashes: {thread_hashes}")
        except Exception as e:
            logger.error(f"Error in post_x_update: {e}\n{traceback.format_exc()}")
        await asyncio.sleep(14400)

@bot.command()
async def crypto_update(ctx):
    try:
        coin_data = await get_ta_data()
        message = "🚀 **Crypto Market Update** 📈\n\n"
        for data in coin_data[:4]:
            try:
                coin_id = [k for k, v in coin_names.items() if v == data['coin']][0]
                news = await fetch_news(data['coin'])
                top_project = data['top_projects'][0][0] if data['top_projects'] else "N/A"
                project_url = data['top_projects'][0][2] if data['top_projects'] and data['top_projects'][0][2] and data['top_projects'][0][2] != "N/A" else ""
                tx_volume = format_number(data['onchain_metrics']['transaction_volume'])
                headline = news['headline'][:100] if news['headline'] else "No headline available"
                token_key = token_symbols.get(coin_id, data['coin'].upper())
                message += (
                    f"**{data['coin']} ({token_key})**\n"
                    f"Price: ${data['text'].split('$')[1]} ({data['price_change_24h']:.2f}% 24h) {'📈' if data['price_change_24h'] > 0 else '📉'}\n"
                )
                if data['predicted_price'] != "N/A":
                    message += f"Predicted Price: {data['predicted_price']} ({data['prediction_explanation']})\n"
                message += (
                    f"Transaction Volume: {tx_volume}\n"
                    f"Active Addresses (Proxy): {data['onchain_metrics']['active_addresses_proxy']}\n"
                    f"Developer Activity: {data['onchain_metrics']['developer_activity']}\n"
                    f"Projects: {data['total_projects']}, Top: {top_project}" + (f" {project_url}" if project_url else "") + "\n"
                    f"News: {headline}\n"
                    f"Link: {news['url']}\n"
                    f"Chart: {data['chart_url']}\n\n"
                )
            except Exception as e:
                logger.error(f"Error processing coin {data['coin']} for Discord message: {e}")
                continue

        content_data = await curate_content([data['coin'].lower() for data in coin_data[:4]], coin_names)
        influencers_list = []
        for coin in content_data:
            if content_data[coin]['x_accounts'] != "No accounts curated":
                influencers_list.extend(content_data[coin]['x_accounts'].split(", "))
        unique_influencers = []
        seen_handles = set()
        for influencer in influencers_list:
            handle = influencer.split(" (")[0]
            if handle not in seen_handles:
                unique_influencers.append(influencer)
                seen_handles.add(handle)
        if unique_influencers:
            message += f"**Stay tuned!** Follow on Twitter/X: {', '.join(unique_influencers[:3])} #CryptoNews"
        else:
            message += "**Stay tuned for more updates!** #CryptoNews"
        await send_discord_message(ctx.channel.id, message)
        await ctx.send("Posted crypto update!")
    except Exception as e:
        logger.error(f"Error in crypto_update command: {e}\n{traceback.format_exc()}")
        await ctx.send("Error posting crypto update. Please try again later.")

@bot.event
async def on_ready():
    logger.info(f"Bot logged in as {bot.user}")
    bot.loop.create_task(post_x_update())

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))