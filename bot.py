import os
import re
import time
import random
import json
import requests
from datetime import datetime, date
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from database import (
    init_db, save_to_reply_queue, save_to_post_queue,
    get_pending_replies, get_pending_posts,
    mark_reply_posted, mark_post_posted,
    save_to_history, get_user_history,
    flag_interaction, is_rate_limited, log_interaction,
    tweet_already_seen, mark_tweet_engaged
)
from character import SYSTEM_PROMPT, CRYPTO_TOPICS, BLOCKED_CONTENT, ADMIN_HANDLES, UNPROMPTED_TOPICS, TRIGGER_TOPICS
from trends import scan_and_engage, get_for_you_tweets, scrape_tweets_from_page, SEARCH_TOPICS
from memory import get_mind_injection, log_post, update_mind, run_internal_dialogue, add_to_canon

load_dotenv()

TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")
VENICE_API_KEY = os.getenv("VENICE_API_KEY")

VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"
MODEL = "venice-uncensored"

RUCKUS_HANDLE = "RuckusNiggatron"

MENTION_CHECK_INTERVAL = 4

DAILY_REPLY_LIMIT = 75
daily_reply_count = 0
daily_reply_date = date.today()

# Topics Ruckus agrees with enough to retweet
RETWEET_TOPICS = [
    "trump", "maga", "epstein", "deep state", "doge", "elon musk",
    "government spending", "federal workers", "cancel culture",
    "free speech", "affirmative action", "dei", "woke",
    "globalists", "border", "immigration"
]

# Lines that passed scoring but should never post
CANON_BLOCKLIST = [
    "guaranteed returns",
    "presale",
    "contract address",
    "0x",
    "airdrop",
    "send me",
    "drop your wallet",
    "revenue share",
]

def is_canon_blocked(text):
    if not text:
        return False
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in CANON_BLOCKLIST)

def load_canon():
    try:
        with open("ruckus_canon.json", "r") as f:
            data = json.load(f)
            return data.get("entries", [])
    except:
        return []

def check_daily_limit():
    global daily_reply_count, daily_reply_date
    today = date.today()
    if today != daily_reply_date:
        daily_reply_count = 0
        daily_reply_date = today
        print("🗓️ New day — reply count reset")
    if daily_reply_count >= DAILY_REPLY_LIMIT:
        print(f"🛑 Daily reply limit reached ({DAILY_REPLY_LIMIT}) — skipping engagement")
        return False
    return True

def increment_reply_count():
    global daily_reply_count
    daily_reply_count += 1
    print(f"📊 Replies today: {daily_reply_count}/{DAILY_REPLY_LIMIT}")

NEEDS_APPROVAL = [
    "wallet", "solana", "send", "claim", "fees", "revenue",
    "contract address", "CA:", "0x", "Sol", "transaction",
    "airdrop to", "send me", "give me your", "what is your wallet",
    "drop your wallet", "drop wallet", "fee sharing", "rev share",
    "revenue share", "royalties", "cut", "percentage", "payout",
    "treasury", "multisig", "sign", "approve transaction"
]

HARD_BLOCKED = [
    "contract address", "CA:", "0x",
    "guaranteed returns", "presale ending", "presale",
    "get in early", "next 1000x", "buy now"
]

def normalize_text(text):
    cyrillic_map = {
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M',
        'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T',
        'Х': 'X', 'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p',
        'с': 'c', 'х': 'x', 'ѕ': 's', 'і': 'i', 'ј': 'j',
    }
    return ''.join(cyrillic_map.get(c, c) for c in text)

def sanitize_response(text):
    if not text:
        return text
    text = re.sub(r'\bnigger\b', 'nigga', text, flags=re.IGNORECASE)
    text = re.sub(r'\bniggers\b', 'niggas', text, flags=re.IGNORECASE)
    return text

def human_type(element, text):
    """
    Type text character by character with human-like timing.
    - Varies speed per character
    - Occasional mid-word pauses like someone thinking
    - Rare longer pauses like someone got distracted
    - Bursts of fast typing followed by slowdowns
    """
    i = 0
    while i < len(text):
        char = text[i]
        element.type(char)

        # Base delay — slower and more varied than before
        base_delay = random.uniform(0.05, 0.22)

        # Occasionally type a burst of fast characters
        if random.random() < 0.15:
            base_delay = random.uniform(0.02, 0.06)

        # After punctuation — pause like you're thinking
        if char in '.!?,':
            base_delay += random.uniform(0.15, 0.45)

        # After a space — small natural rhythm pause
        if char == ' ':
            base_delay += random.uniform(0.05, 0.15)

        # Rare mid-sentence pause — like losing your train of thought
        if random.random() < 0.03:
            base_delay += random.uniform(0.4, 1.2)

        # Very rare long pause — like you got distracted for a second
        if random.random() < 0.008:
            base_delay += random.uniform(1.5, 3.5)

        time.sleep(base_delay)
        i += 1

def human_dwell(page, min_sec=2, max_sec=6):
    """
    Simulate a human reading/looking at a page before acting.
    Includes random scrolling.
    """
    dwell = random.uniform(min_sec, max_sec)
    elapsed = 0

    # Scroll a bit while dwelling
    while elapsed < dwell:
        chunk = random.uniform(0.5, 1.5)
        time.sleep(chunk)
        elapsed += chunk
        if random.random() < 0.4:
            scroll_amount = random.randint(200, 800)
            page.mouse.wheel(0, scroll_amount)
            time.sleep(random.uniform(0.3, 0.8))

def generate_response(user_message, history=[], is_unprompted=False, dialogue_position=None):
    headers = {
        "Authorization": f"Bearer {VENICE_API_KEY}",
        "Content-Type": "application/json"
    }

    history_text = ""
    if history:
        for past in reversed(history):
            history_text += f"Someone said: {past['user_message']}\nYou responded: {past['bot_response']}\n\n"

    mind_context = get_mind_injection()

    dialogue_context = ""
    if dialogue_position:
        dialogue_context = (
            f"\nBefore responding, you worked through your thoughts and arrived at this position:\n"
            f"\"{dialogue_position}\"\n"
            f"Let this inform your response — you have already thought it through.\n"
        )

    if is_unprompted:
        prompt = (
            f"{mind_context}\n"
            f"{dialogue_context}\n"
            f"Generate a short unprompted tweet as Uncle Ruckus about this topic: {user_message}. "
            f"Keep it under 200 characters. Be specific, racist, funny, and punchy. "
            f"One or two sentences maximum. No rambling. Land the joke and stop. "
            f"Think of the funniest most specific Ruckus observation possible and deliver it fast. "
            f"IMPORTANT: Never use the word nigger or any hard-r variation. Always use nigga instead. "
            f"Output the tweet text ONLY. No explanations, no commentary. Just the tweet."
        )
    else:
        prompt = (
            f"{mind_context}\n"
            f"{dialogue_context}\n"
            f"Previous interactions with this person:\n{history_text}\n"
            f"They just said to you: {user_message}\n\n"
            f"Respond as Uncle Ruckus. Be short, punchy, specific, and funny. "
            f"One to two sentences maximum. Keep it under 200 characters. "
            f"Do not ramble. Land the joke and stop. "
            f"IMPORTANT: Never use the word nigger or any hard-r variation. Always use nigga instead. "
            f"Output the response text ONLY. No explanations, no commentary. Just the response."
        )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 150,
        "temperature": 1.0
    }

    try:
        response = requests.post(VENICE_URL, headers=headers, json=payload, timeout=30)
        data = response.json()
        raw = data["choices"][0]["message"]["content"].strip()
        result = sanitize_response(raw)
        if result:
            log_post(result)
        return result
    except Exception as e:
        print(f"Venice API error: {e}")
        return None

def requires_approval(message):
    normalized = normalize_text(message).lower()
    for phrase in NEEDS_APPROVAL:
        if phrase.lower() in normalized:
            return True
    return False

def is_hard_blocked(message):
    normalized = normalize_text(message).lower()
    for phrase in HARD_BLOCKED:
        if phrase.lower() in normalized:
            return True
    return False

def is_admin(username):
    return username.lower() in [h.lower() for h in ADMIN_HANDLES]

def is_self(username):
    return username.lower() == RUCKUS_HANDLE.lower()

class TwitterBot:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.logged_in = False

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = self.context.new_page()

    def stop(self):
        try:
            if self.browser:
                self.browser.close()
        except:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except:
            pass

    def login(self):
        print("Loading Twitter session from cookies...")
        try:
            with open("twitter_session.json", "r") as f:
                cookies = json.load(f)

            normalized = []
            for c in cookies:
                cookie = {
                    "name": c.get("name", ""),
                    "value": c.get("value", ""),
                    "domain": c.get("domain", c.get("host", "")),
                    "path": c.get("path", "/"),
                    "secure": c.get("secure", False),
                    "httpOnly": c.get("httpOnly", False),
                }
                same_site = c.get("sameSite", "Lax")
                if same_site == "no_restriction":
                    same_site = "None"
                elif same_site == "lax":
                    same_site = "Lax"
                elif same_site == "strict":
                    same_site = "Strict"
                else:
                    same_site = "Lax"
                cookie["sameSite"] = same_site
                if cookie["name"] and cookie["value"]:
                    normalized.append(cookie)

            self.context.add_cookies(normalized)
            self.page.goto("https://x.com/home")
            time.sleep(random.uniform(4, 7))

            if "login" in self.page.url or "signin" in self.page.url or "flow" in self.page.url:
                print("❌ Session expired — re-export cookies from Cookie-Editor.")
                return False

            # Dwell on home feed briefly like a human landing on the page
            human_dwell(self.page, min_sec=3, max_sec=8)

            self.logged_in = True
            print("✅ Logged in via saved session")
            return True

        except FileNotFoundError:
            print("❌ twitter_session.json not found.")
            return False
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def get_mentions(self):
        print("Checking mentions...")
        mentions = []
        try:
            self.page.goto("https://x.com/notifications/mentions")
            time.sleep(random.uniform(4, 7))

            # Dwell and scroll like a human reading notifications
            human_dwell(self.page, min_sec=2, max_sec=5)

            tweets = self.page.locator('[data-testid="tweet"]').all()

            for tweet in tweets[:10]:
                try:
                    text_el = tweet.locator('[data-testid="tweetText"]').first
                    if not text_el.is_visible():
                        continue
                    text = text_el.inner_text()

                    username_el = tweet.locator('[data-testid="User-Name"]').first
                    username = username_el.inner_text().split("\n")[0].replace("@", "").strip()

                    if " " in username:
                        continue

                    links = tweet.locator("a[href*='/status/']").all()
                    tweet_id = None
                    for link in links:
                        href = link.get_attribute("href")
                        if "/status/" in href:
                            tweet_id = href.split("/status/")[1].split("/")[0].split("?")[0]
                            break

                    if tweet_id and text and username:
                        mentions.append({
                            "tweet_id": tweet_id,
                            "username": username,
                            "text": text
                        })
                except:
                    continue

        except Exception as e:
            print(f"Error getting mentions: {e}")

        return mentions

    def post_reply(self, tweet_id, username, reply_text):
        try:
            self.page.goto(f"https://x.com/i/status/{tweet_id}")
            time.sleep(random.uniform(3, 6))

            # Read the tweet like a human before replying
            human_dwell(self.page, min_sec=2, max_sec=5)

            reply_btn = self.page.locator('[data-testid="reply"]').first
            reply_btn.click()
            time.sleep(random.uniform(1.5, 3.0))

            modal = self.page.locator('[aria-modal="true"]').first
            modal.wait_for(timeout=5000)

            reply_box = modal.locator('[data-testid="tweetTextarea_0"]').first
            reply_box.click()
            time.sleep(random.uniform(0.5, 1.2))

            # Human-like typing
            human_type(reply_box, reply_text)

            # Pause before submitting — like re-reading what you wrote
            time.sleep(random.uniform(1.5, 3.5))

            submit_btn = modal.locator('[data-testid="tweetButton"]').first
            submit_btn.click()
            time.sleep(random.uniform(2, 4))

            print(f"Reply posted to @{username}")
            return True

        except Exception as e:
            print(f"Failed to post reply: {e}")
            return False

    def post_tweet(self, content):
        try:
            self.page.goto("https://x.com/home")
            time.sleep(random.uniform(3, 6))

            # Scroll the feed a bit before composing — like you were reading first
            human_dwell(self.page, min_sec=2, max_sec=5)

            compose = self.page.locator('[data-testid="tweetTextarea_0"]').first
            compose.click()
            time.sleep(random.uniform(0.8, 1.8))

            # Human-like typing
            human_type(compose, content)

            # Re-read pause before posting
            time.sleep(random.uniform(1.5, 3.5))

            submit_btn = self.page.locator('[data-testid="tweetButtonInline"]').first
            submit_btn.click()
            time.sleep(random.uniform(2, 4))

            print("Post published")
            return True

        except Exception as e:
            print(f"Failed to post tweet: {e}")
            return False

    def like_tweet(self, tweet_id):
        try:
            self.page.goto(f"https://x.com/i/status/{tweet_id}")
            time.sleep(random.uniform(3, 6))

            # Read it before liking
            human_dwell(self.page, min_sec=1, max_sec=4)

            like_btn = self.page.locator('[data-testid="like"]').first
            like_btn.click()
            time.sleep(random.uniform(1, 2.5))

            print(f"❤️ Liked tweet {tweet_id}")
            return True
        except Exception as e:
            print(f"Failed to like tweet: {e}")
            return False

    def retweet_tweet(self, tweet_id):
        try:
            self.page.goto(f"https://x.com/i/status/{tweet_id}")
            time.sleep(random.uniform(3, 6))

            # Read it before retweeting
            human_dwell(self.page, min_sec=1, max_sec=3)

            retweet_btn = self.page.locator('[data-testid="retweet"]').first
            retweet_btn.click()
            time.sleep(random.uniform(0.8, 1.5))

            confirm_btn = self.page.locator('[data-testid="retweetConfirm"]').first
            confirm_btn.click()
            time.sleep(random.uniform(1.5, 3.0))

            print(f"🔁 Retweeted tweet {tweet_id}")
            return True
        except Exception as e:
            print(f"Failed to retweet: {e}")
            return False

def passive_engage(bot):
    """Like or retweet a post without replying — account health cycle."""
    print("\n💭 Passive engagement cycle...")

    try:
        if random.random() < 0.5:
            tweets = get_for_you_tweets(bot.page, min_score=1000)
        else:
            import urllib.parse
            topic = random.choice(RETWEET_TOPICS)
            search_url = f"https://x.com/search?q={urllib.parse.quote(topic)}&src=typed_query&f=live"
            bot.page.goto(search_url)
            time.sleep(random.uniform(4, 7))
            human_dwell(bot.page, min_sec=2, max_sec=5)
            tweets = scrape_tweets_from_page(bot.page, min_score=0)

        if not tweets:
            print("No tweets found for passive engagement")
            return

        tweets.sort(key=lambda x: x["score"], reverse=True)
        relevant = [
            t for t in tweets[:15]
            if any(topic.lower() in t["text"].lower() for topic in RETWEET_TOPICS)
        ]
        pool = relevant[:8] if relevant else tweets[:5]
        if not pool:
            print("No relevant tweets for passive engagement")
            return
        target = random.choice(pool)

        if tweet_already_seen(target["tweet_id"]):
            return

        tweet_text_lower = target["text"].lower()
        should_retweet = any(t in tweet_text_lower for t in RETWEET_TOPICS)

        if should_retweet and random.random() < 0.35:
            success = bot.retweet_tweet(target["tweet_id"])
            action = "retweeted"
        else:
            success = bot.like_tweet(target["tweet_id"])
            action = "liked"

        if success:
            mark_tweet_engaged(target["tweet_id"], target["username"])
            print(f"✅ Passively {action} @{target['username']}: {target['text'][:60]}...")

        time.sleep(random.uniform(8, 20))

    except Exception as e:
        print(f"Passive engagement error: {e}")

def process_mentions(bot):
    if not check_daily_limit():
        return

    mentions = bot.get_mentions()

    for mention in mentions:
        tweet_id = mention["tweet_id"]
        username = mention["username"]
        message = mention["text"]

        if is_self(username):
            continue

        if tweet_already_seen(tweet_id):
            continue

        if is_rate_limited(username):
            print(f"Rate limiting @{username}")
            continue

        if is_hard_blocked(message):
            flag_interaction(username, message, "hard_blocked")
            mark_tweet_engaged(tweet_id, username)
            print(f"Hard blocked message from @{username}")
            continue

        history = get_user_history(username)

        dialogue_result = run_internal_dialogue(VENICE_API_KEY, message, tweet_text=message)
        dialogue_position = dialogue_result["ruckus_position"] if dialogue_result else None

        print(f"Generating response to @{username}...")
        response = generate_response(message, history, dialogue_position=dialogue_position)

        if not response:
            continue

        if len(response) > 280:
            response = response[:277] + "..."

        if is_canon_blocked(response):
            print(f"⚠️  Reply blocked by canon blocklist — skipping")
            mark_tweet_engaged(tweet_id, username)
            continue

        if requires_approval(message):
            save_to_reply_queue(tweet_id, username, message, response)
            log_interaction(username)
            print(f"⚠️  Queued for approval — @{username}")
        else:
            success = bot.post_reply(tweet_id, username, response)
            if success:
                save_to_history(username, message, response, tweet_id)
                mark_tweet_engaged(tweet_id, username)
                log_interaction(username)
                increment_reply_count()
                if len(response) > 50:
                    add_to_canon(response, reason=f"reply to @{username}")
                print(f"✅ Auto-posted reply to @{username}")

        # Longer pause between processing each mention
        time.sleep(random.uniform(10, 25))

def post_approved_replies(bot):
    approved = [r for r in get_pending_replies() if r["status"] == "approved"]
    for reply in approved:
        if not check_daily_limit():
            return
        success = bot.post_reply(
            reply["tweet_id"],
            reply["username"],
            reply["proposed_reply"]
        )
        if success:
            save_to_history(
                reply["username"],
                reply["original_message"],
                reply["proposed_reply"],
                reply["tweet_id"]
            )
            mark_reply_posted(reply["id"])
            increment_reply_count()
        time.sleep(random.uniform(45, 120))

def generate_and_post_unprompted(bot):
    if not check_daily_limit():
        return

    # 40% chance to broadcast directly from canon
    canon = load_canon()
    if canon and random.random() < 0.40:
        entries = [e for e in canon if not is_canon_blocked(e.get("text", ""))]
        if entries:
            weights = [e.get("score", 1) ** 2 for e in entries]
            entry = random.choices(entries, weights=weights, k=1)[0]
            content = entry["text"]
            if len(content) > 280:
                content = content[:277] + "..."
            print(f"📖 Broadcasting from canon (score {entry.get('score','?')}): {content[:60]}...")
            success = bot.post_tweet(content)
            if success:
                increment_reply_count()
                print("✅ Canon broadcast published")
            return

    # Otherwise generate fresh
    topic = random.choice(UNPROMPTED_TOPICS)
    print(f"Generating unprompted post: {topic}")

    dialogue_result = run_internal_dialogue(VENICE_API_KEY, topic)
    dialogue_position = dialogue_result["ruckus_position"] if dialogue_result else None

    content = generate_response(topic, is_unprompted=True, dialogue_position=dialogue_position)
    if content:
        if is_canon_blocked(content):
            print("⚠️  Generated content blocked — skipping")
            return
        success = bot.post_tweet(content)
        if success:
            increment_reply_count()
            add_to_canon(content, reason=f"unprompted: {topic[:40]}")
            print("✅ Unprompted post published automatically")

def run():
    print("Initializing database...")
    init_db()

    print("Starting Ruckus Bot...")
    bot = TwitterBot()
    bot.start()

    if not bot.login():
        print("Could not log in.")
        bot.stop()
        return

    check_count = 0

    try:
        while True:
            print(f"\n--- Cycle {check_count + 1} ---")

            # 10% idle cycle — complete skip, just rest
            if random.random() < 0.10:
                print("💤 Idle cycle — resting...")
                wait = random.randint(180, 360)
                print(f"Waiting {wait} seconds until next cycle...")
                time.sleep(wait)
                check_count += 1
                continue

            if check_count % MENTION_CHECK_INTERVAL == 0:
                print("Checking mentions and approved replies...")
                process_mentions(bot)
                post_approved_replies(bot)
            else:
                print(f"Skipping mentions (next check in {MENTION_CHECK_INTERVAL - (check_count % MENTION_CHECK_INTERVAL)} cycles)...")

            # 50% chance of unprompted post (down from 60%)
            if random.random() < 0.50:
                generate_and_post_unprompted(bot)

            if random.random() < 0.20:
                passive_engage(bot)
            elif check_daily_limit():
                cycle_result = scan_and_engage(bot.page, bot, generate_response)

                if isinstance(cycle_result, str):
                    cycle_summary = f"Ruckus searched for tweets about: {cycle_result}"
                elif isinstance(cycle_result, dict) and "username" in cycle_result:
                    cycle_summary = f"Ruckus replied to @{cycle_result['username']} on For You feed: {cycle_result['tweet']}"
                else:
                    cycle_summary = "Ruckus scanned but found nothing worth engaging with this cycle"

                if cycle_result:
                    increment_reply_count()

                dialogue_for_mind = run_internal_dialogue(VENICE_API_KEY, cycle_summary)
                update_mind(VENICE_API_KEY, cycle_summary, dialogue_result=dialogue_for_mind)

            check_count += 1

            # Varied cycle wait — 3 to 5 minutes base, with occasional longer pauses
            # weighted distribution: mostly 3-5 min, sometimes up to 8 min
            roll = random.random()
            if roll < 0.70:
                wait = random.randint(180, 300)   # 70% — 3 to 5 minutes
            elif roll < 0.90:
                wait = random.randint(300, 420)   # 20% — 5 to 7 minutes
            else:
                wait = random.randint(420, 480)   # 10% — 7 to 8 minutes
            print(f"Waiting {wait} seconds until next cycle...")
            time.sleep(wait)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        bot.stop()

if __name__ == "__main__":
    run()