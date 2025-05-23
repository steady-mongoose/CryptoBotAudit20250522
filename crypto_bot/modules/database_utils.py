# c:\CryptoBot\crypto_bot\modules\database_utils.py
import sqlite3
import logging
import os

lg = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'data', db_path)
        self._create_tables()
        self._populate_coins()

    def _create_tables(self):
        """Create the necessary tables in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS coins (
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        symbol TEXT
                    )
                ''')
                conn.commit()
                lg.info(f"Created tables in {self.db_path}")
        except Exception as e:
            lg.error(f"Error creating tables: {e}")

    def _populate_coins(self):
        """Populate the coins table with the coins from the X post."""
        try:
            coins = [
                ("ripple", "Ripple", "XRP"),
                ("hedera-hashgraph", "Hedera Hashgraph", "HBAR"),
                ("stellar", "Stellar", "XLM"),
                ("xdc-network", "XDC Network", "XDC"),
                ("sui", "Sui", "SUI"),
                ("ondo", "Ondo", "ONDO"),
                ("algorand", "Algorand", "ALGO"),
                ("casper", "Casper", "CSPR"),
            ]
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.executemany("INSERT OR IGNORE INTO coins (id, name, symbol) VALUES (?, ?, ?)", coins)
                conn.commit()
                lg.info("Populated coins table with initial data")
        except Exception as e:
            lg.error(f"Error populating coins table: {e}")

    def get_top_coins(self):
        """Retrieve the list of coins to track."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, symbol FROM coins")
                coins = [{"id": row[0], "name": row[1], "symbol": row[2]} for row in cursor.fetchall()]
                return coins
        except Exception as e:
            lg.error(f"Error fetching top coins: {e}")
            return []