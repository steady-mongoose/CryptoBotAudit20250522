# c:\CryptoBot\crypto_bot\modules\social_media_utils.py
import logging
import tweepy
import asyncio

lg = logging.getLogger(__name__)

async def post_x_thread(x_client, posts):
    """Post a thread on X."""
    if not x_client:
        lg.error("X client not initialized")
        return

    try:
        previous_tweet = None
        for i, post in enumerate(posts):
            if i == 0:
                # Post the first tweet
                response = x_client.create_tweet(text=post)
                previous_tweet = response.data['id']
                lg.info(f"Posted main tweet: {post}")
            else:
                # Post subsequent tweets as replies
                response = x_client.create_tweet(text=post, in_reply_to_tweet_id=previous_tweet)
                previous_tweet = response.data['id']
                lg.info(f"Posted reply tweet: {post}")
            # Add a small delay to avoid rate limits
            await asyncio.sleep(1)

    except tweepy.TweepyException as e:
        lg.error(f"Error posting X thread: {e}")
    except Exception as e:
        lg.error(f"Unexpected error posting X thread: {e}")

async def coat_tail_reply(x_client, original_tweet_id, reply_text):
    """Post a reply to an existing tweet (coat-tailing)."""
    if not x_client:
        lg.error("X client not initialized")
        return

    try:
        response = x_client.create_tweet(text=reply_text, in_reply_to_tweet_id=original_tweet_id)
        lg.info(f"Posted coat-tail reply to tweet {original_tweet_id}: {reply_text}")
    except tweepy.TweepyException as e:
        lg.error(f"Error posting coat-tail reply: {e}")
    except Exception as e:
        lg.error(f"Unexpected error posting coat-tail reply: {e}")

async def follow_crypto_users(x_client):
    """Follow a list of influential crypto users on X."""
    if not x_client:
        lg.error("X client not initialized")
        return

    # List of influential crypto users (usernames)
    crypto_users = [
        "VitalikButerin",
        "cz_binance",
        "brian_armstrong",
        "SBF_FTX",
        "el33th4xor"
    ]

    for username in crypto_users:
        try:
            # Fetch user data
            user = x_client.get_user(username=username)
            if not user.data:
                lg.warning(f"Could not find user: {username}")
                continue

            # Attempt to follow the user
            x_client.follow_user(user.data.id)
            lg.info(f"Followed user: {username}")

            # Add a small delay between follow requests to avoid rate limits
            await asyncio.sleep(1)

        except tweepy.TweepyException as e:
            lg.error(f"Error following {username}: {e}")
            continue
        except Exception as e:
            lg.error(f"Unexpected error following {username}: {e}")
            continue