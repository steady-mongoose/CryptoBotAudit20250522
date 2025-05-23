import logging
import aiohttp

lg = logging.getLogger(__name__)


async def fetch_projs(coin, session, db_path):
    """Fetch projects for a given coin (mock implementation)."""
    lg.info(f'Fetching projects for coin: {coin}')

    # Mock project data
    project_mapping = {
        'ripple': ('RippleNet', 'Payment Protocol', 'https://ripple.com/ripplenet'),
        'hedera-hashgraph': ('Hedera Consensus Service', 'Decentralized Infrastructure', 'https://hedera.com'),
        'stellar': ('Stellar Development Foundation', 'Cross-Border Payments', 'https://stellar.org'),
        'xdce-crowd-sale': ('XinFin', 'Hybrid Blockchain', 'https://xinfin.org'),
        'sui': ('Sui Blockchain', 'Layer 1 Blockchain', 'https://sui.io'),
        'ondo-finance': ('Ondo Protocol', 'DeFi Lending', 'https://ondo.finance'),
        'algorand': ('Algorand Foundation', 'Blockchain Protocol', 'https://algorand.foundation'),
        'casper': ('Casper Network', 'Proof-of-Stake Blockchain', 'https://casper.network'),
        'bitcoin': ('Bitcoin Core', 'Decentralized Currency', 'https://bitcoin.org'),
        'ethereum': ('Ethereum Foundation', 'Smart Contract Platform', 'https://ethereum.org')
    }

    project = project_mapping.get(coin)
    if project:
        lg.info(f'Found project for {coin}: {project}')
        return project
    else:
        lg.warning(f'No project found for {coin}')
        return ('Unknown', 'N/A', 'N/A')