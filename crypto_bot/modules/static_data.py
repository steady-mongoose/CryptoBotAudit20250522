"""Static data for the CryptoBot project.

This module contains static configuration data such as coin mappings, TradingView symbols,
hashtags, project stats, project details, and price averages used across the bot.
"""

# Mapping of CoinGecko coin IDs to display names
cn = {
    'ripple': 'Ripple',
    'hedera-hashgraph': 'Hedera Hashgraph',
    'stellar': 'Stellar',
    'xdce-crowd-sale': 'XDC',
    'sui': 'Sui',
    'ondo-finance': 'Ondo',
    'algorand': 'Algorand',
    'casper': 'Casper'
}

# Mapping of CoinGecko coin IDs to TradingView symbols
cs = {
    'ripple': 'XRPUSD',
    'hedera-hashgraph': 'HBARUSD',
    'stellar': 'XLMUSD',
    'xdce-crowd-sale': 'XDCUSD',
    'sui': 'SUIUSD',
    'ondo-finance': 'ONDOUSD',
    'algorand': 'ALGOUSD',
    'casper': 'CSPRUSD'
}

# Hashtags for each coin
htags = {
    'XRP': ['#XRPL', '#XRPArmy'],
    'HBAR': ['#Hedera', '#Hashgraph'],
    'XLM': ['#Stellar', '#StellarLumens'],
    'XDC': ['#XDCNetwork', '#TradeFinance'],
    'SUI': ['#SuiNetwork', '#DeFi'],
    'ONDO': ['#OndoFinance', '#RWA'],
    'ALGO': ['#Algorand', '#GreenCrypto'],
    'CSPR': ['#CasperNetwork', '#EnterpriseBlockchain']
}

# Static project stats
sps = {
    'ripple': {'count': 50, 'source': 'RippleX', 'url': 'https://ripplex.io/', 'partnerships': 20, 'total_projects': 150},
    'hedera-hashgraph': {'count': 100, 'source': 'Hedera.com', 'url': 'https://hedera.com/ecosystem', 'partnerships': 30, 'total_projects': 200},
    'stellar': {'count': 200, 'source': 'Stellar.org', 'url': 'https://www.stellar.org/ecosystem/projects', 'partnerships': 25, 'total_projects': 250},
    'xdce-crowd-sale': {'count': 50, 'source': 'XinFin.org', 'url': 'https://xinfin.org/ecosystem', 'partnerships': 15, 'total_projects': 100},
    'sui': {'count': 150, 'source': 'Sui.io', 'url': 'https://sui.io/ecosystem', 'partnerships': 20, 'total_projects': 300},
    'ondo-finance': {'count': 80, 'source': 'Ondo.finance', 'url': 'https://ondo.finance/ecosystem', 'partnerships': 10, 'total_projects': 120},
    'algorand': {'count': 200, 'source': 'Algorand.com', 'url': 'https://algorand.com/ecosystem', 'partnerships': 30, 'total_projects': 350},
    'casper': {'count': 100, 'source': 'Casper.network', 'url': 'https://casper.network/ecosystem', 'partnerships': 15, 'total_projects': 200}
}

# Static project details
sdp = {
    'ripple': [('Sologenic', 'Tokenizes assets like stocks on XRPL', 'https://sologenic.org'), ('XRPL Labs', 'Building Xumm wallet for XRPL', 'https://xrpl-labs.com')],
    'hedera-hashgraph': [('SaucerSwap', 'DeFi DEX on Hedera', 'https://saucerswap.finance'), ('Hashport', 'Cross-chain bridge for Hedera', 'https://hashport.network')],
    'stellar': [('StellarAid', 'Charity payments on Stellar', 'https://stellaraid.org'), ('Vibrant', 'Mobile wallet for Stellar', 'https://vibrant.io')],
    'xdce-crowd-sale': [('TradeFinex', 'Trade finance on XDC', 'https://tradefinex.org'), ('XDC Network', 'Hybrid blockchain solutions', 'https://xdc.network')],
    'sui': [('Cetus', 'DeFi protocol on Sui', 'https://cetus.zone'), ('Navi Protocol', 'Lending protocol on Sui', 'https://naviprotocol.io')],
    'ondo-finance': [('Ondo Vaults', 'Structured finance on Ondo', 'https://ondo.finance/vaults'), ('Flux', 'Tokenized assets on Ondo', 'https://ondo.finance/flux')],
    'algorand': [('Algofi', 'DeFi lending on Algorand', 'https://algofi.org'), ('Folks Finance', 'Lending and borrowing on Algorand', 'https://folks.finance')],
    'casper': [('CasperPad', 'Launchpad on Casper', 'https://www.coingecko.com/en/coins/casperpad'), ('CasperLabs', 'Enterprise blockchain solutions', 'https://casperlabs.io')]
}

# Static price averages
spya = {
    'ripple': 0.60,
    'hedera-hashgraph': 0.09,
    'stellar': 0.11,
    'xdce-crowd-sale': 0.03,
    'sui': 0.80,
    'ondo-finance': 0.25,
    'algorand': 0.15,
    'casper': 0.04
}