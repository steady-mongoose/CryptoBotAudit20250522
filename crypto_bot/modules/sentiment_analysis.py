import logging
import os
import aiohttp

# Setup logging
lg = logging.getLogger(__name__)

async def fetch_sentiment_data(session, coin):
    """Fetch sentiment data for a given coin using LunarCrush API."""
    lunarcrush_api_key = os.getenv('LUNARCRUSH_API_KEY')
    if not lunarcrush_api_key:
        lg.error("LUNARCRUSH_API_KEY environment variable not set")
        return {'bullish_percent': 0, 'bearish_percent': 0, 'galaxy_score': 0}

    # Map coin to LunarCrush symbol
    coin_mapping = {
        'SUI': 'sui',
        'XRP': 'xrp'
    }
    coin_symbol = coin_mapping.get(coin, coin.lower())

    url = f"https://api.lunarcrush.com/v3/coins/{coin_symbol}/insights?key={lunarcrush_api_key}"
    sentiment_data = {
        'bullish_percent': 0,
        'bearish_percent': 0,
        'galaxy_score': 0
    }

    try:
        async with session.get(url) as response:
            if response.status != 200:
                lg.error(f"LunarCrush API error for {coin}: {response.status} - {await response.text()}")
                return sentiment_data
            data = await response.json()
            sentiment = data.get('sentiment', {})
            sentiment_data['bullish_percent'] = sentiment.get('bullish', 0)
            sentiment_data['bearish_percent'] = sentiment.get('bearish', 0)
            sentiment_data['galaxy_score'] = data.get('galaxy_score', 0)
    except Exception as e:
        lg.error(f"Error fetching LunarCrush data for {coin}: {e}")

    return sentiment_data