import sqlite3  # Added for database operations
import json
import hashlib
import logging
from datetime import datetime, UTC

# Setup logging
lg = logging.getLogger(__name__)


def load_history(db_path):
    """Load thread history from the database."""
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute('SELECT data FROM thread_history WHERE rowid=1')
        row = cur.fetchone()
        if row:
            try:
                history = json.loads(row[0])
                lg.debug(f'Loaded history: {history}')
                return history
            except json.JSONDecodeError:
                lg.error('Failed to decode thread history JSON')
                return []
        lg.debug('No thread history found')
        return []


def save_history(history, db_path):
    """Save thread history to the database."""
    lg.debug(f'Saving history: {history}')
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute('INSERT OR REPLACE INTO thread_history (rowid, data) VALUES (1, ?)', (json.dumps(history),))
        conn.commit()


def prune_history(history):
    """Prune thread history to keep only the last 30 days of entries."""
    threshold = datetime.now(UTC).timestamp() - (30 * 86400)  # 30 days ago
    pruned = [entry for entry in history if entry['timestamp'] >= threshold]
    lg.debug(f'Pruned history from {len(history)} to {len(pruned)} entries')
    return pruned


def hash_post(post):
    """Generate a hash for a post to check for duplicates."""
    return hashlib.sha256(post.encode('utf-8')).hexdigest()


def is_thread_unique(thread, history, significant_events):
    """Check if the thread is unique compared to recent history."""
    lg.debug(f'Checking thread uniqueness with history length: {len(history)}')
    # Prune history to keep only recent entries (last 24 hours)
    recent_history = [entry for entry in history if (datetime.now(UTC).timestamp() - entry['timestamp']) < 86400]
    lg.debug(f'Recent history (last 24 hours) length: {len(recent_history)}')

    # Generate hashes for the current thread
    thread_hashes = [hash_post(p) for p in thread]
    lg.debug(f'Current thread hashes: {thread_hashes}')

    # Check for duplicates in recent history
    recent_hashes = set()
    for entry in recent_history:
        recent_hashes.update(entry['post_hashes'])
    lg.debug(f'Recent history hashes: {recent_hashes}')

    # Check if any thread part is a duplicate
    for th in thread_hashes:
        if th in recent_hashes:
            lg.debug(f'Duplicate found: {th}')
            return False

    # Check for significant events that might justify reposting
    if significant_events:
        lg.debug(f'Significant events detected, allowing repost: {significant_events}')
        return True

    lg.debug('Thread is unique')
    return True


def score_influencers(inf, ts):
    """Placeholder for scoring influencers (not implemented). Accepts inf and ts for compatibility."""
    lg.debug(f'score_influencers called with inf: {inf}, ts: {ts}')
    return []  # Placeholder: return empty list