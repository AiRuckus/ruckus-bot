import sqlite3
from datetime import datetime, timedelta

DB_NAME = "ruckus.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS reply_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT UNIQUE,
            username TEXT,
            original_message TEXT,
            proposed_reply TEXT,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            actioned_at DATETIME
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            user_message TEXT,
            bot_response TEXT,
            tweet_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS post_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            posted_at DATETIME
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS flagged (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            message TEXT,
            reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            interaction_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS engaged_tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT UNIQUE,
            username TEXT,
            engaged_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

def save_to_reply_queue(tweet_id, username, message, proposed_reply):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO reply_queue (tweet_id, username, original_message, proposed_reply)
            VALUES (?, ?, ?, ?)
        """, (tweet_id, username, message, proposed_reply))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_pending_replies():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM reply_queue 
        WHERE status = 'pending'
        ORDER BY created_at ASC
    """)
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_pending_posts():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM post_queue
        WHERE status = 'pending'
        ORDER BY created_at ASC
    """)
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def approve_reply(reply_id, edited_reply=None):
    conn = get_connection()
    c = conn.cursor()
    if edited_reply:
        c.execute("""
            UPDATE reply_queue 
            SET status = 'approved', proposed_reply = ?, actioned_at = ?
            WHERE id = ?
        """, (edited_reply, datetime.now(), reply_id))
    else:
        c.execute("""
            UPDATE reply_queue 
            SET status = 'approved', actioned_at = ?
            WHERE id = ?
        """, (datetime.now(), reply_id))
    conn.commit()
    conn.close()

def deny_reply(reply_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE reply_queue 
        SET status = 'denied', actioned_at = ?
        WHERE id = ?
    """, (datetime.now(), reply_id))
    conn.commit()
    conn.close()

def approve_post(post_id, edited_content=None):
    conn = get_connection()
    c = conn.cursor()
    if edited_content:
        c.execute("""
            UPDATE post_queue
            SET status = 'approved', content = ?, actioned_at = ?
            WHERE id = ?
        """, (edited_content, datetime.now(), post_id))
    else:
        c.execute("""
            UPDATE post_queue
            SET status = 'approved', actioned_at = ?
            WHERE id = ?
        """, (datetime.now(), post_id))
    conn.commit()
    conn.close()

def deny_post(post_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE post_queue
        SET status = 'denied', actioned_at = ?
        WHERE id = ?
    """, (datetime.now(), post_id))
    conn.commit()
    conn.close()

def mark_reply_posted(reply_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE reply_queue SET status = 'posted' WHERE id = ?
    """, (reply_id,))
    conn.commit()
    conn.close()

def mark_post_posted(post_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE post_queue SET status = 'posted', posted_at = ?
        WHERE id = ?
    """, (datetime.now(), post_id))
    conn.commit()
    conn.close()

def save_to_history(username, user_message, bot_response, tweet_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO conversation_history 
        (username, user_message, bot_response, tweet_id)
        VALUES (?, ?, ?, ?)
    """, (username, user_message, bot_response, tweet_id))
    conn.commit()
    conn.close()

def get_user_history(username, limit=5):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT user_message, bot_response 
        FROM conversation_history
        WHERE username = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (username, limit))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def flag_interaction(username, message, reason):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO flagged (username, message, reason)
        VALUES (?, ?, ?)
    """, (username, message, reason))
    conn.commit()
    conn.close()

def is_rate_limited(username, max_per_hour=10):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) as count FROM rate_limits
        WHERE username = ?
        AND interaction_time > datetime('now', '-1 hour')
    """, (username,))
    result = c.fetchone()
    conn.close()
    return result['count'] >= max_per_hour

def log_interaction(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO rate_limits (username)
        VALUES (?)
    """, (username,))
    conn.commit()
    conn.close()

def save_to_post_queue(content):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO post_queue (content)
        VALUES (?)
    """, (content,))
    conn.commit()
    conn.close()

def tweet_already_seen(tweet_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM reply_queue WHERE tweet_id = ?", (tweet_id,))
    if c.fetchone():
        conn.close()
        return True
    c.execute("SELECT id FROM engaged_tweets WHERE tweet_id = ?", (tweet_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_tweet_engaged(tweet_id, username):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO engaged_tweets (tweet_id, username)
            VALUES (?, ?)
        """, (tweet_id, username))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_recent_engaged_tweets(hours=24):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT tweet_id, engaged_at FROM engaged_tweets
        WHERE engaged_at > datetime('now', ?)
    """, (f'-{hours} hours',))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

if __name__ == "__main__":
    init_db()