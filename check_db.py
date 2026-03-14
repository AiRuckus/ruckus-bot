import sqlite3

conn = sqlite3.connect('ruckus.db')
c = conn.cursor()

print('=== TABLES ===')
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print([r[0] for r in c.fetchall()])

print('\n=== ENGAGED TWEETS (last 10) ===')
c.execute('SELECT tweet_id, username, engaged_at FROM engaged_tweets ORDER BY engaged_at DESC LIMIT 10')
for r in c.fetchall(): print(r)

print('\n=== CONVERSATION HISTORY (last 10) ===')
c.execute('SELECT username, user_message, bot_response, created_at FROM conversation_history ORDER BY created_at DESC LIMIT 10')
for r in c.fetchall(): print(r)

print('\n=== REPLY QUEUE (last 10) ===')
c.execute('SELECT tweet_id, username, status, created_at FROM reply_queue ORDER BY created_at DESC LIMIT 10')
for r in c.fetchall(): print(r)

print('\n=== POST QUEUE (last 10) ===')
c.execute('SELECT content, status, created_at FROM post_queue ORDER BY created_at DESC LIMIT 10')
for r in c.fetchall(): print(r)

conn.close()