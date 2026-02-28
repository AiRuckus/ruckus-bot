import re
import time
import random
import urllib.parse
from datetime import datetime, timedelta
from database import mark_tweet_engaged, get_recent_engaged_tweets, tweet_already_seen

# ─────────────────────────────────────────
# ENGAGEMENT SETTINGS
# ─────────────────────────────────────────

MIN_SCORE = 2000
TWEET_COOLDOWN_MINUTES = 60
FEED_COOLDOWN_MIN = 15
FEED_COOLDOWN_MAX = 45
SEARCH_COOLDOWN_MINUTES = 20

RECENCY_HOURS = 6
RECENCY_DECAY = 0.5
MAX_TWEET_AGE_HOURS = 24

RUCKUS_HANDLE = "ruckusniggatron"

# Topics Ruckus actively searches — the culture he lives in
SEARCH_TOPICS = [
    "black excellence", "black pride", "reparations", "white privilege",
    "systemic racism", "black lives matter", "afrocentrism", "juneteenth",
    "trump", "maga", "liberal", "woke", "cancel culture", "dei",
    "doge", "elon musk", "government spending", "federal workers",
    "epstein", "deep state", "conspiracy", "globalists",
    "looksmaxxing", "sigma male", "andrew tate", "manosphere", "incel",
    "crypto", "bitcoin", "memecoin", "nft", "rugpull", "shitcoin",
    "trans rights", "gender pronouns", "defund police", "affirmative action",
    "immigration", "border", "gun control", "free speech",
    "skibidi", "brain rot", "gen z", "rizz", "aura",
    "black twitter", "hotep", "black owned",
]

engaged_tweets = {}
last_feed_scan = None
last_search_scan = None

def load_engaged_from_db():
    recent = get_recent_engaged_tweets(hours=24)
    for row in recent:
        try:
            engaged_at = datetime.fromisoformat(row["engaged_at"])
            engaged_tweets[row["tweet_id"]] = engaged_at
        except:
            pass
    print(f"Loaded {len(engaged_tweets)} recent engagements from database")

load_engaged_from_db()

# ─────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────

def calculate_engagement_score(likes, retweets, replies, impressions=0, age_hours=0):
    score = (likes * 1) + (retweets * 3) + (replies * 2)
    if impressions > 0:
        score = score * (1 + (impressions / 1000000))
    if age_hours > RECENCY_HOURS:
        score *= RECENCY_DECAY
    return score

def parse_count(text):
    if not text:
        return 0
    text = text.strip().upper().replace(",", "")
    try:
        if "K" in text:
            return int(float(text.replace("K", "")) * 1000)
        elif "M" in text:
            return int(float(text.replace("M", "")) * 1000000)
        else:
            return int(text)
    except:
        return 0

def get_tweet_age_hours(tweet):
    try:
        time_el = tweet.locator("time").first
        datetime_attr = time_el.get_attribute("datetime")
        if datetime_attr:
            tweet_time = datetime.fromisoformat(datetime_attr.replace("Z", "+00:00"))
            tweet_time = tweet_time.replace(tzinfo=None)
            age = datetime.utcnow() - tweet_time
            return age.total_seconds() / 3600
    except:
        pass
    return 999

def is_on_cooldown(tweet_id):
    if tweet_id in engaged_tweets:
        elapsed = datetime.now() - engaged_tweets[tweet_id]
        if elapsed < timedelta(minutes=TWEET_COOLDOWN_MINUTES):
            return True
    return False

def feed_on_cooldown():
    global last_feed_scan
    if last_feed_scan is None:
        return False
    elapsed = datetime.now() - last_feed_scan
    cooldown = timedelta(minutes=random.randint(FEED_COOLDOWN_MIN, FEED_COOLDOWN_MAX))
    return elapsed < cooldown

def search_on_cooldown():
    global last_search_scan
    if last_search_scan is None:
        return False
    elapsed = datetime.now() - last_search_scan
    return elapsed < timedelta(minutes=SEARCH_COOLDOWN_MINUTES)

def mark_engaged(tweet_id, username="unknown"):
    engaged_tweets[tweet_id] = datetime.now()
    mark_tweet_engaged(tweet_id, username)

# ─────────────────────────────────────────
# RETWEET CHECK
# ─────────────────────────────────────────

def is_retweet(tweet):
    try:
        social_context = tweet.locator('[data-testid="socialContext"]').first
        text = social_context.inner_text(timeout=1000).strip()
        if "reposted" in text.lower() or "retweeted" in text.lower():
            return True
    except:
        pass
    return False

# ─────────────────────────────────────────
# SCRAPE TWEETS FROM CURRENT PAGE
# ─────────────────────────────────────────

def scrape_tweets_from_page(page, min_score=500):
    tweets = []
    try:
        page.mouse.wheel(0, 1500)
        time.sleep(2)
        page.mouse.wheel(0, 1500)
        time.sleep(1)

        tweet_elements = page.locator('[data-testid="tweet"]').all()

        for tweet in tweet_elements:
            try:
                if is_retweet(tweet):
                    continue

                text_el = tweet.locator('[data-testid="tweetText"]').first
                if not text_el.is_visible():
                    continue
                text = text_el.inner_text()

                if len(text) < 15:
                    continue

                username_el = tweet.locator('[data-testid="User-Name"]').first
                username = username_el.inner_text().split("\n")[0].replace("@", "").strip()

                if username.lower() == RUCKUS_HANDLE:
                    continue

                if " " in username:
                    continue

                links = tweet.locator("a[href*='/status/']").all()
                tweet_id = None
                for link in links:
                    href = link.get_attribute("href")
                    if "/status/" in href:
                        tweet_id = href.split("/status/")[1].split("/")[0].split("?")[0]
                        break

                if not tweet_id:
                    continue

                if tweet_already_seen(tweet_id):
                    continue

                if is_on_cooldown(tweet_id):
                    continue

                age_hours = get_tweet_age_hours(tweet)
                if age_hours > MAX_TWEET_AGE_HOURS:
                    continue

                likes = retweets = replies = impressions = 0

                try:
                    likes = parse_count(tweet.locator('[data-testid="like"]').first.inner_text().strip())
                except:
                    pass
                try:
                    retweets = parse_count(tweet.locator('[data-testid="retweet"]').first.inner_text().strip())
                except:
                    pass
                try:
                    replies = parse_count(tweet.locator('[data-testid="reply"]').first.inner_text().strip())
                except:
                    pass
                try:
                    analytics = tweet.locator('[data-testid="app-text-transition-container"]').all()
                    for a in analytics:
                        val = parse_count(a.inner_text())
                        if val > impressions:
                            impressions = val
                except:
                    pass

                score = calculate_engagement_score(likes, retweets, replies, impressions, age_hours)

                if score >= min_score:
                    tweets.append({
                        "tweet_id": tweet_id,
                        "username": username,
                        "text": text,
                        "likes": likes,
                        "retweets": retweets,
                        "replies": replies,
                        "impressions": impressions,
                        "score": score,
                        "age_hours": age_hours
                    })

            except:
                continue

    except Exception as e:
        print(f"Error scraping page: {e}")

    return tweets

# ─────────────────────────────────────────
# GENERATE KOL-AWARE RESPONSE PROMPT
# ─────────────────────────────────────────

NO_EXPLAIN = (
    "Output the response text ONLY. "
    "No explanations, no commentary, no analysis of why it is funny, "
    "no labels, no preamble. Just the raw tweet text and nothing else."
)

# ─────────────────────────────────────────
# DIRECT TOPIC SEARCH AND ENGAGE
# Replaces wander_and_engage — no trending scrape needed
# ─────────────────────────────────────────

def search_and_engage(page, bot, generate_response_fn):
    global last_search_scan

    if search_on_cooldown():
        print("Search on cooldown")
        return False

    last_search_scan = datetime.now()

    topic = random.choice(SEARCH_TOPICS)
    print(f"\n🔍 Searching for tweets about: {topic}")

    try:
        search_url = f"https://x.com/search?q={urllib.parse.quote(topic)}&src=typed_query&f=live"
        page.goto(search_url)
        time.sleep(random.uniform(5, 8))
    except Exception as e:
        print(f"Search navigation error: {e}")
        return False

    tweets = scrape_tweets_from_page(page, min_score=500)

    if not tweets:
        print(f"No tweets found for: {topic}")
        return False

    tweets.sort(key=lambda x: x["score"], reverse=True)
    top_tweets = tweets[:5]
    best = random.choice(top_tweets)

    print(f"Selected tweet from @{best['username']} — score: {best['score']} | age: {best['age_hours']:.1f}h | topic: {topic}")

    prompt = (
        f"You just saw this tweet about \"{topic}\":\n\n"
        f"\"{best['text']}\"\n\n"
        f"React to it as Uncle Ruckus in your signature style. "
        f"Be short, punchy, specific, and funny. One to two sentences maximum. "
        f"Keep it under 200 characters. Land the joke and stop. "
        f"{NO_EXPLAIN}"
    )

    response = generate_response_fn(prompt)

    if not response:
        return False

    if len(response) > 280:
        response = response[:277] + "..."

    success = bot.post_reply(best["tweet_id"], best["username"], response)

    if success:
        mark_engaged(best["tweet_id"], best["username"])
        print(f"✅ Replied to @{best['username']} on topic: {topic}")
        time.sleep(random.randint(60, 180))
        return topic

    return False

# ─────────────────────────────────────────
# FOR YOU FEED SCRAPER
# ─────────────────────────────────────────

def get_for_you_tweets(page, min_score=MIN_SCORE):
    tweets = []
    try:
        print("Navigating to For You feed...")
        page.goto("https://x.com/home")
        time.sleep(5)

        page.mouse.wheel(0, 1500)
        time.sleep(2)
        page.mouse.wheel(0, 1500)
        time.sleep(2)

        tweet_elements = page.locator('[data-testid="tweet"]').all()
        print(f"Found {len(tweet_elements)} posts in For You feed")

        for tweet in tweet_elements:
            try:
                if is_retweet(tweet):
                    continue

                text_el = tweet.locator('[data-testid="tweetText"]').first
                if not text_el.is_visible():
                    continue
                text = text_el.inner_text()

                if len(text) < 15:
                    continue

                username_el = tweet.locator('[data-testid="User-Name"]').first
                username = username_el.inner_text().split("\n")[0].replace("@", "").strip()

                if username.lower() == RUCKUS_HANDLE:
                    continue

                if " " in username:
                    continue

                links = tweet.locator("a[href*='/status/']").all()
                tweet_id = None
                for link in links:
                    href = link.get_attribute("href")
                    if "/status/" in href:
                        tweet_id = href.split("/status/")[1].split("/")[0].split("?")[0]
                        break

                if not tweet_id:
                    continue

                if tweet_already_seen(tweet_id):
                    continue

                age_hours = get_tweet_age_hours(tweet)
                if age_hours > MAX_TWEET_AGE_HOURS:
                    continue

                if is_on_cooldown(tweet_id):
                    continue

                likes = retweets = replies = impressions = 0

                try:
                    likes = parse_count(tweet.locator('[data-testid="like"]').first.inner_text().strip())
                except:
                    pass
                try:
                    retweets = parse_count(tweet.locator('[data-testid="retweet"]').first.inner_text().strip())
                except:
                    pass
                try:
                    replies = parse_count(tweet.locator('[data-testid="reply"]').first.inner_text().strip())
                except:
                    pass
                try:
                    analytics = tweet.locator('[data-testid="app-text-transition-container"]').all()
                    for a in analytics:
                        val = parse_count(a.inner_text())
                        if val > impressions:
                            impressions = val
                except:
                    pass

                score = calculate_engagement_score(likes, retweets, replies, impressions, age_hours)

                if score >= min_score:
                    tweets.append({
                        "tweet_id": tweet_id,
                        "username": username,
                        "text": text,
                        "likes": likes,
                        "retweets": retweets,
                        "replies": replies,
                        "impressions": impressions,
                        "score": score,
                        "age_hours": age_hours
                    })

            except:
                continue

    except Exception as e:
        print(f"Error scraping For You feed: {e}")

    return tweets

# ─────────────────────────────────────────
# FOR YOU FEED ENGAGE
# ─────────────────────────────────────────

def engage_for_you_feed(page, bot, generate_response_fn):
    global last_feed_scan

    if feed_on_cooldown():
        print("For You feed on cooldown")
        return False

    print("\n🔍 Scanning For You feed...")
    last_feed_scan = datetime.now()

    trending = get_for_you_tweets(page)

    if not trending:
        print("No recent posts found above threshold in For You feed")
        return False

    trending.sort(key=lambda x: x["score"], reverse=True)
    top_posts = trending[:3]
    best = random.choice(top_posts)

    print(f"Selected post from @{best['username']} — score: {best['score']} | age: {best['age_hours']:.1f}h")

    prompt = (
        f"You just saw this viral post from @{best['username']} on your timeline:\n\n"
        f"\"{best['text']}\"\n\n"
        f"It has {best['likes']} likes and {best['retweets']} retweets — clearly going viral.\n"
        f"React to it as Uncle Ruckus in your signature style. "
        f"Be short, punchy, specific, and funny. One to two sentences maximum. "
        f"Keep it under 200 characters. Land the joke and stop. "
        f"{NO_EXPLAIN}"
    )

    response = generate_response_fn(prompt)

    if not response:
        return False

    if len(response) > 280:
        response = response[:277] + "..."

    success = bot.post_reply(best["tweet_id"], best["username"], response)

    if success:
        mark_engaged(best["tweet_id"], best["username"])
        print(f"✅ Replied to @{best['username']}")
        time.sleep(random.randint(60, 180))
        return {"username": best["username"], "tweet": best["text"][:100]}

    return False

# ─────────────────────────────────────────
# MAIN SCAN AND ENGAGE
# 50% topic search, 50% For You feed
# ─────────────────────────────────────────

def scan_and_engage(page, bot, generate_response_fn):
    roll = random.random()

    if roll < 0.50:
        result = search_and_engage(page, bot, generate_response_fn)
        if not result:
            result = engage_for_you_feed(page, bot, generate_response_fn)
        return result
    else:
        result = engage_for_you_feed(page, bot, generate_response_fn)
        if not result:
            result = search_and_engage(page, bot, generate_response_fn)
        return result
