from datetime import datetime

WHITEPAPER_OVERVIEWS = {
    'XDC-NETWORK': (
        "XinFin's XDC Network leverages a Delegated Proof-of-Stake (DPoS) consensus with 108 masternodes, ensuring low-cost, fast transactions (2000+ TPS, 2-second finality). It focuses on trade finance and real-world asset tokenization, with smart contracts for transparency in global trade workflows. Challenges include competition with established players like Ethereum in the tokenization space."
    ),
    'ONDO': (
        "Ondo Finance bridges DeFi and traditional finance by tokenizing real-world assets (RWAs) like U.S. Treasuries. Its governance model uses the ONDO token for voting on protocol upgrades, aiming for decentralized management of financial products. Challenges include regulatory hurdles and reliance on stablecoin stability for its tokenized products."
    ),
    'STELLAR': (
        "Stellar focuses on cross-border payments with its Stellar Consensus Protocol (SCP), enabling fast (3-5 sec finality) and cheap transactions. It supports smart contracts for token issuance, targeting financial inclusion. Challenges include adoption hurdles in traditional finance and competition with Ripple in the remittance market."
    ),
    'ALGORAND': (
        "Algorand uses a Pure Proof-of-Stake (PPoS) consensus, offering high scalability (1000+ TPS, 4.5-sec finality) and low fees. It supports smart contracts and asset tokenization, focusing on DeFi and CBDCs. Challenges include limited developer adoption compared to Ethereum and scaling its ecosystem for mainstream use."
    ),
}

def get_coin_update_thread(coins_data, news_dict, youtube_videos, metrics, now):
    """Generate a thread for the crypto market update."""
    date_str = now.strftime("%Y-%m-%d")
    main_post = f"🚀 Crypto Market Update ({date_str})! 📈 Latest on top altcoins: Ripple, Hedera Hashgraph, Stellar, XDC, Sui, Ondo, Algorand, Casper. #Crypto #Altcoins"
    thread = [main_post]

    for coin, data in coins_data.items():
        symbol = coin.upper()
        price = data.get('price', 0)
        price_change = data.get('price_change_24h', 0)
        predicted_price = data.get('predicted_price', price)
        tx_volume = data.get('tx_volume', 0)
        top_project = data.get('top_projects', [('N/A', '')])[0][0]
        news = news_dict.get(coin, [('No recent news found', f"https://t.co/placeholder_{coin}")])
        news_title, news_url = news[0] if news else ('No recent news found', f"https://t.co/placeholder_{coin}")
        direction = "📈" if price_change >= 0 else "📉"
        post = (
            f"{coin.lower()} ({symbol}): ${price:.2f} ({price_change:.2f}% 24h) {direction}\n"
            f"Predicted: ${predicted_price:.2f} (Linear regression)\n"
            f"Tx Volume: {tx_volume/1_000_000:.2f}M\n"
            f"Top Project: {top_project}\n"
            f"News: {news_title} {news_url}\n"
            f"#{symbol}"
        )
        thread.append(post)

    # Add on-chain metrics for Ripple (XRP)
    tx_volume_m = metrics.get('tx_volume', 0) / 1_000_000
    active_addresses_m = metrics.get('active_addresses', 0) / 1_000_000
    whale_activity = metrics.get('whale_activity', 0)
    onchain_post = (
        f"📊 On-Chain Insights: Ripple (XRP) 🪙\n"
        f"XRPL processed {tx_volume_m:.2f}M transactions in the last 24h, with a 7-day avg of {active_addresses_m:.2f}M active addresses. "
        f"Whale activity is {'up' if whale_activity >= 0 else 'down'} {abs(whale_activity):.1f}%—a {'bullish' if whale_activity >= 0 else 'bearish'} signal? 🐳 "
        f"#Ripple #XRP #OnChain"
    )
    thread.append(onchain_post)

    # Add YouTube video summaries
    video_post = "📹 Crypto Video Updates:\n"
    for title, url in youtube_videos[:2]:
        video_post += f"{title}: {url}\n"
    video_post += "#CryptoNews #Blockchain"
    thread.append(video_post)

    # Add engagement question
    thread.append("Which altcoin are you most excited about today? 🚀 Drop your thoughts below! 👇 #Crypto #Altcoins")
    return thread

def get_onchain_metrics_thread(metrics):
    """Generate a thread for on-chain metrics."""
    tx_volume_m = metrics.get('tx_volume', 0) / 1_000_000
    active_addresses_m = metrics.get('active_addresses', 0) / 1_000_000
    whale_activity = metrics.get('whale_activity', 0)

    main_post = "📊 XRP On-Chain Metrics Update 🪙 #XRP #Ripple #OnChain"
    thread = [main_post]

    thread.append(
        f"💸 Transaction Volume (24h): {tx_volume_m:.2f}M transactions on the XRP Ledger. High activity signals strong network usage! #XRPL"
    )
    thread.append(
        f"👥 Active Addresses (7d avg): {active_addresses_m:.2f}M addresses. Consistent growth here reflects user engagement. #Ripple"
    )
    thread.append(
        f"🐳 Whale Activity: Large tx volume {'up' if whale_activity >= 0 else 'down'} {abs(whale_activity):.1f}% over the past week. "
        f"{'Big players are accumulating—bullish?' if whale_activity >= 0 else 'Whales are quiet—bearish signal?'} #XRP"
    )
    thread.append(
        "What do these metrics tell you about XRP’s momentum? Share your analysis below! 👇 #CryptoAnalysis"
    )
    return thread

def get_tokenization_trends_thread():
    """Generate a thread on tokenization trends."""
    main_post = "🏦 Tokenization Trends: Real-World Assets on the Blockchain 🌐 #Tokenization #Blockchain #RWA"
    thread = [main_post]

    thread.append(
        "Tokenization is transforming finance by bringing real-world assets (RWAs) on-chain—think real estate, bonds, and commodities. "
        "This thread dives into XDC Network and Ondo, two altcoins leading the charge! 🚀 #RWA"
    )
    thread.append(
        f"🌍 XDC Network: {WHITEPAPER_OVERVIEWS['XDC-NETWORK']}\n"
        f"XDC is carving a niche in trade finance—could it redefine global trade? #XDC"
    )
    thread.append(
        f"💸 Ondo Finance: {WHITEPAPER_OVERVIEWS['ONDO']}\n"
        f"Ondo’s focus on tokenized financial products bridges DeFi and TradFi—game-changer or regulatory risk? #ONDO"
    )
    thread.append(
        "Tokenization could hit $10T in market value by 2030! Which RWA projects are you watching? 🧐 #CryptoTrends"
    )
    return thread

def get_multichain_projects_thread():
    """Generate a thread on multi-chain projects."""
    main_post = "🌐 Multi-Chain Projects: Scaling Blockchain for the Future 🔗 #MultiChain #Blockchain #Crypto"
    thread = [main_post]

    thread.append(
        "Multi-chain ecosystems enhance scalability and interoperability, enabling seamless cross-chain transactions. "
        "Let’s explore Stellar and Algorand—two altcoins pushing the boundaries! 🚀 #Interoperability"
    )
    thread.append(
        f"💸 Stellar: {WHITEPAPER_OVERVIEWS['STELLAR']}\n"
        f"Stellar’s focus on cross-border payments—can it outpace Ripple? #Stellar #XLM"
    )
    thread.append(
        f"🌍 Algorand: {WHITEPAPER_OVERVIEWS['ALGORAND']}\n"
        f"Algorand’s PPoS offers scalability for DeFi and CBDCs—next big thing? #Algorand #ALGO"
    )
    thread.append(
        "Multi-chain solutions are key to blockchain’s future! Which projects do you think will dominate? 🤔 #CryptoFuture"
    )
    return thread

def get_sentiment_analysis_thread(sui_sentiment, xrp_sentiment):
    """Generate a thread on market sentiment analysis."""
    main_post = "📣 Market Sentiment Analysis: SUI and XRP in Focus 🧠 #CryptoSentiment #MarketAnalysis"
    thread = [main_post]

    thread.append(
        "Understanding market sentiment helps gauge investor confidence. Using LunarCrush data, let’s break down SUI and XRP! 📊 #Crypto"
    )
    sui_bullish = sui_sentiment.get('bullish_percent', 0)
    sui_bearish = sui_sentiment.get('bearish_percent', 0)
    sui_galaxy_score = sui_sentiment.get('galaxy_score', 0)
    thread.append(
        f"💧 SUI Sentiment:\n"
        f"Bullish: {sui_bullish:.1f}% 🟢\n"
        f"Bearish: {sui_bearish:.1f}% 🔴\n"
        f"Galaxy Score: {sui_galaxy_score:.1f}/100 (Social Engagement)\n"
        f"{'Positive vibes—SUI might be gearing up for a move!' if sui_bullish > sui_bearish else 'Caution: Bearish sentiment dominates.'} #SUI"
    )
    xrp_bullish = xrp_sentiment.get('bullish_percent', 0)
    xrp_bearish = xrp_sentiment.get('bearish_percent', 0)
    xrp_galaxy_score = xrp_sentiment.get('galaxy_score', 0)
    thread.append(
        f"💸 XRP Sentiment:\n"
        f"Bullish: {xrp_bullish:.1f}% 🟢\n"
        f"Bearish: {xrp_bearish:.1f}% 🔴\n"
        f"Galaxy Score: {xrp_galaxy_score:.1f}/100 (Social Engagement)\n"
        f"{'XRP bulls are in control—uptrend incoming?' if xrp_bullish > xrp_bearish else 'Bears are lurking—watch for downside risk.'} #XRP"
    )
    thread.append(
        "Sentiment drives markets—how are you feeling about SUI and XRP? Share your thoughts! 👇 #CryptoInsights"
    )
    return thread