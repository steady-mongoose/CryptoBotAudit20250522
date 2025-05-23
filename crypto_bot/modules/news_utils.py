# c:\CryptoBot\crypto_bot\modules\news_utils.py
import logging
from gnews import GNews

lg = logging.getLogger(__name__)

async def fetch_news(coin_ids, session):
    """
    Fetch news articles for the given coin IDs using Google News.
    """
    try:
        # Map coin IDs to search terms (e.g., use symbols or names for better results)
        coin_search_terms = {
            "ripple": "XRP",
            "hedera-hashgraph": "Hedera HBAR",
            "stellar": "Stellar XLM",
            "xdc-network": "XDC Network",
            "sui": "Sui crypto",
            "ondo": "Ondo crypto",
            "algorand": "Algorand ALGO",
            "casper": "Casper CSPR",
        }

        google_news = GNews(language='en', country='US', max_results=1)
        news_dict = {}

        for coin_id in coin_ids:
            search_term = coin_search_terms.get(coin_id, coin_id)
            lg.info(f"Fetching news for {coin_id} using search term: {search_term}")
            news = google_news.get_news(search_term)
            if news:
                news_dict[coin_id] = [
                    {
                        "title": article["title"],
                        "url": article["url"]
                    }
                    for article in news
                ]
            else:
                news_dict[coin_id] = []
                lg.warning(f"No news found for {coin_id}")

        return news_dict

    except Exception as e:
        lg.error(f"Error fetching news: {e}")
        # Fallback mock news data based on the X post
        return {
            "ripple": [{"title": "CME XRP futures debut hits $15M in daily volume", "url": "https://t.co/rX1DAwfHzz"}],
            "hedera-hashgraph": [{"title": "HBAR price prediction: How THESE price levels could dictate its next move", "url": "https://t.co/XmTFbSnXVP"}],
            "stellar": [{"title": "Stellar Blade™", "url": "https://t.co/nPBN2hqxJL"}],
            "xdc-network": [],
            "sui": [{"title": "New lawsuit filings: Genesis creditors accuse Barry Silbert of fraud", "url": "https://t.co/g97FguZyj8"}],
            "ondo": [{"title": "World leader in digital assets? Toronto emerges as a global blockchain hotspot", "url": "https://t.co/VbtBhbm25H"}],
            "algorand": [{"title": "sysstra 0.1.3.4.0", "url": "https://t.co/TtGTsuf6wv"}],
            "casper": [{"title": "JUCO big man Stephen Osei commits to Kansas State", "url": "https://t.co/xF3vLwFZ5i"}],
        }