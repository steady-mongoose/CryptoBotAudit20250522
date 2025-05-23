import sqlite3
import os
from datetime import datetime, UTC, timedelta
from contextlib import contextmanager  # Added import for context manager support

def get_db(db_path):
    """Context manager for SQLite database connections."""
    @contextmanager
    def db_connection():
        conn = sqlite3.connect(db_path)
        try:
            yield conn
        finally:
            conn.close()
    return db_connection()

def init_db(db_path):
    """Initialize the SQLite database with required tables."""
    with get_db(db_path) as conn:
        cur = conn.cursor()
        # Create news_cache table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS news_cache (
                coin TEXT PRIMARY KEY,
                data TEXT,
                last_updated INTEGER
            )
        ''')
        # Create history table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                post_hashes TEXT,
                influencers TEXT
            )
        ''')
        # Create top_coins table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS top_coins (
                coin_id TEXT PRIMARY KEY,
                display_name TEXT,
                rank INTEGER
            )
        ''')
        # Check if top_coins is empty, and populate with default coins if necessary
        cur.execute('SELECT COUNT(*) FROM top_coins')
        count = cur.fetchone()[0]
        if count == 0:
            default_coins = [
                ('ripple', 'Ripple', 1),
                ('hedera-hashgraph', 'Hedera Hashgraph', 2),
                ('stellar', 'Stellar', 3),
                ('xdce-crowd-sale', 'XDC', 4),
                ('sui', 'Sui', 5),
                ('ondo-finance', 'Ondo', 6),
                ('algorand', 'Algorand', 7),
                ('casper', 'Casper', 8),
                ('bitcoin', 'Bitcoin', 9),
                ('ethereum', 'Ethereum', 10)
            ]
            cur.executemany('INSERT INTO top_coins (coin_id, display_name, rank) VALUES (?, ?, ?)', default_coins)
            conn.commit()
        conn.commit()

def clean_cache(db_path):
    """Clean old cache entries from the database."""
    threshold = (datetime.now(UTC) - timedelta(days=1)).timestamp()
    with get_db(db_path) as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM news_cache WHERE last_updated < ?', (threshold,))
        conn.commit()

def fmt_num(num):
    """Format a number for display."""
    try:
        num = float(num)
        if num >= 1_000_000:
            return f'{num / 1_000_000:.2f}M'
        elif num >= 1_000:
            return f'{num / 1_000:.2f}K'
        else:
            return f'{num:.2f}'
    except (TypeError, ValueError):
        return 'N/A'