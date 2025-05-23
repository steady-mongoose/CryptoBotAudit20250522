# c:\CryptoBot\crypto_bot\modules\content_utils.py
import logging
from datetime import datetime
import discord

lg = logging.getLogger(__name__)


def create_thread_content(coins_data, news_dict, youtube_videos, santiment_metrics):
    """
    Create thread content for posting to X.
    """
    try:
        # Main post
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        posts = [f"🚀 Crypto Market Update ({current_date})! 📈 Latest on top altcoins: #Crypto #Altcoins"]

        # Add coin data
        for coin in coins_data:
            change = coin['percent_change_24h']
            trend = "📈" if change >= 0 else "📉"
            tx_volume = santiment_metrics.get(coin['id'], {}).get("transaction_volume", 0)
            post = (
                f"{coin['id'].replace('-', ' ').upper()}: ${coin['price']} ({change}% 24h) {trend}\n"
                f"Tx Volume: {tx_volume}M\n"
                f"Top Project: N/A"
            )
            if coin['id'] in news_dict and news_dict[coin['id']]:
                news = news_dict[coin['id']][0]
                post += f"\nNews: {news['title']} {news['url']}\n#{coin['id'].replace('-', '').upper()}"
            posts.append(post)

        # Add YouTube videos
        if youtube_videos:
            posts.append("📹 Crypto Video Updates:")
            for video in youtube_videos:
                posts.append(f"{video['title']}: {video['url']}")
            posts[-1] += "\n#CryptoNews #Blockchain"

        # Add a call to action
        posts.append("Which altcoin are you most excited about today? 🚀 Drop your thoughts below! 👇 #Crypto #Altcoins")

        return posts

    except Exception as e:
        lg.error(f"Error creating thread content: {e}")
        return []


async def post_discord_update(channel, coins_data, news_dict, youtube_videos):
    """
    Post the crypto update to Discord as an embed.
    """
    try:
        embed = discord.Embed(title="🚀 Crypto Market Update", color=0x00ff00, timestamp=datetime.utcnow())

        for coin in coins_data:
            change = coin['percent_change_24h']
            trend = "📈" if change >= 0 else "📉"
            embed.add_field(
                name=f"{coin['id'].replace('-', ' ').upper()} {trend}",
                value=f"Price: ${coin['price']} ({change}% 24h)",
                inline=False
            )
            if coin['id'] in news_dict and news_dict[coin['id']]:
                news = news_dict[coin['id']][0]
                embed.add_field(
                    name="News",
                    value=f"[{news['title']}]({news['url']})",
                    inline=False
                )

        if youtube_videos:
            embed.add_field(
                name="📹 YouTube Updates",
                value="\n".join([f"[{video['title']}]({video['url']})" for video in youtube_videos]),
                inline=False
            )

        await channel.send(embed=embed)
        lg.info(f"Sent Discord message to channel {channel.id}: {len(embed.fields)} fields")

    except Exception as e:
        lg.error(f"Error posting Discord update: {e}")