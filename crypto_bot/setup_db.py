import sqlite3

DB_PATH = r"c:\CryptoBot\crypto_bot\modules\..\data\crypto_bot.db"

def setup_database():
    """Set up the SQLite database with top coins."""
    top_coins = [
        "ripple", "hedera-hashgraph", "stellar", "xdc-network",
        "sui", "ondo", "algorand", "casper"
    ]

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS top_coins (
                coin_id TEXT PRIMARY KEY
            )
        """)
        # Insert coins
        for coin in top_coins:
            cursor.execute("INSERT OR REPLACE INTO top_coins (coin_id) VALUES (?)", (coin,))
        conn.commit()
        print(f"Database set up successfully at {DB_PATH} with coins: {top_coins}")
    except sqlite3.Error as e:
        print(f"Error setting up database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_database()