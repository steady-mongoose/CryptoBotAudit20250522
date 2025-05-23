import logging
import aiohttp
import json
from datetime import datetime, UTC, timedelta

lg = logging.getLogger(__name__)

async def send_discord_message(channel_id, messages, bot):
    """Send a list of messages to a Discord channel."""
    try:
        channel = bot.get_channel(channel_id)
        if channel is None:
            lg.error(f'Discord channel {channel_id} not found')
            return False
        # If a single string is passed, convert it to a list
        if isinstance(messages, str):
            messages = [messages]
        for message in messages:
            if len(message) > 2000:
                lg.error(f'Discord message exceeds 2000 characters: {len(message)} chars')
                return False
            await channel.send(message)
            lg.info(f'Sent Discord message to channel {channel_id}: {len(message)} chars')
        return True
    except Exception as e:
        lg.error(f'Discord send err: {e}')
        return False

async def send_x_thread(client, thread):
    """Send a thread to X."""
    try:
        tweet = client.create_tweet(text=thread[0])
        tweet_id = tweet.data['id']
        for post in thread[1:]:
            tweet = client.create_tweet(text=post, in_reply_to_tweet_id=tweet_id)
            tweet_id = tweet.data['id']
        lg.info('Posted X thread')
        return True
    except Exception as e:
        lg.error(f'X post err: {e}')
        return False

async def fetch_news(coin, session, db_path, newsapi_key):
    """Fetch news for a coin from NewsAPI."""
    try:
        url = f'https://newsapi.org/v2/everything?q={coin}+cryptocurrency&sortBy=publishedAt&apiKey={newsapi_key}'
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            data = await response.json()
            articles = data.get('articles', [])
            if articles:
                return articles[0].get('title', f'No news for {coin}'), articles[0].get('url', 'https://example.com')
            return f'No news for {coin}', 'https://example.com'
    except aiohttp.ClientError as e:
        lg.error(f'News fetch err for {coin}: {e}')
        return f'No news for {coin}', 'https://example.com'

async def get_youtube_summary(yt_client, keywords, max_results=2):
    """Fetch recent YouTube videos for given keywords."""
    try:
        # Calculate the timestamp for videos from the last 24 hours
        time_threshold_dt = datetime.now(UTC) - timedelta(days=1)
        # Format the timestamp to exclude microseconds (RFC 3339 format: YYYY-MM-DDThh:mm:ssZ)
        time_threshold = time_threshold_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        request = yt_client.search().list(
            part='snippet',
            q=' '.join(keywords),
            type='video',
            publishedAfter=time_threshold,
            maxResults=max_results,
            order='date'
        )
        response = request.execute()
        videos = response.get('items', [])
        summaries = []
        for video in videos:
            title = video['snippet']['title']
            video_id = video['id']['videoId']
            url = f'https://www.youtube.com/watch?v={video_id}'
            summaries.append(f'{title}: {url}')
        return '\n'.join(summaries) if summaries else 'No recent videos found'
    except Exception as e:
        lg.error(f'YouTube API err: {e}')
        return 'Unable to fetch videos'

async def curate_content(coin, session, db_path):
    """Curate social media content for a coin."""
    try:
        # Placeholder for X follower count or other metrics
        return {'twitter_followers': 0, 'curated_x': 'No accounts curated'}
    except Exception as e:
        lg.error(f'Curate content err for {coin}: {e}')
        return {'twitter_followers': 0, 'curated_x': 'No accounts curated'}