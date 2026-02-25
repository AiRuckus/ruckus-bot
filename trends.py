import time
import random
from datetime import datetime, timedelta

# ─────────────────────────────────────────
# ENGAGEMENT SETTINGS
# ─────────────────────────────────────────

MIN_SCORE = 2000
TWEET_COOLDOWN_MINUTES = 60
FEED_COOLDOWN_MIN = 15
FEED_COOLDOWN_MAX = 45

# Track what we've already engaged with
engaged_tweets = {}
last_feed_scan = None

# ─────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────

def calculate_engagement_score(likes, retweets, replies, impressions=0):
    score = (likes * 1) + (retweets * 3) + (replies * 2)
    if impressions > 0:
        score = score * (1 + (impressions / 1000000))
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

def mark_engaged(tweet_id):
    engaged_tweets[tweet_id] = datetime.now()

def should_quote_tweet(score):
    if score > 50000:
        return random.random() < 0.7
    elif score > 10000:
        return random.random() < 0.4
    else:
        return random.random() < 0.2

# ─────────────────────────────────────────
# FOR YOU FEED SCRAPER
# ─────────────────────────────────────────

def get_for_you_tweets(page, min_score=MIN_SCORE):
    tweets = []
    try:
        print("Navigating to For You feed...")
        page.goto("https://x.com/explore/tabs/for-you")
        time.sleep(5)

        # Scroll to load more posts
        for _ in range(3):
            page.mouse.wheel(0, 1200)
            time.sleep(1.5)

        tweet_elements = page.locator('[data-testid="tweet"]').all()
        print(f"Found {len(tweet_elements)} posts in For You feed")

        for tweet in tweet_elements[:20]:
            try:
                # Get tweet text
                text_el = tweet.locator('[data-testid="tweetText"]')
                if not text_el.is_visible():
                    continue
                text = text_el.inner_text()

                if len(text) < 15:
                    continue

                # Get username
                username_el = tweet.locator('[data-testid="User-Name"]')
                username = username_el.inner_text().split("\n")[0].replace("@", "").strip()

                # Skip Ruckus replying to himself
                if username.lower() == "ruckusniggatron":
                    continue

                # Get tweet ID
                links = tweet.locator("a[href*='/status/']").all()
                tweet_id = None
                for link in links:
                    href = link.get_attribute("href")
                    if "/status/" in href:
                        tweet_id = href.split("/status/")[1].split("/")[0].split("?")[0]
                        break

                if not tweet_id:
                    continue

                if is_on_cooldown(tweet_id):
                    continue

                # Get engagement numbers
                likes = retweets = replies = impressions = 0

                try:
                    like_text = tweet.locator('[data-testid="like"]').inner_text().strip()
                    likes = parse_count(like_text)
                except:
                    pass

                try:
                    retweet_text = tweet.locator('[data-testid="retweet"]').inner_text().strip()
                    retweets = parse_count(retweet_text)
                except:
                    pass

                try:
                    reply_text = tweet.locator('[data-testid="reply"]').inner_text().strip()
                    replies = parse_count(reply_text)
                except:
                    pass

                # Try to get impressions
                try:
                    analytics = tweet.locator('[data-testid="app-text-transition-container"]').all()
                    for a in analytics:
                        val = parse_count(a.inner_text())
                        if val > impressions:
                            impressions = val
                except:
                    pass

                score = calculate_engagement_score(likes, retweets, replies, impressions)

                if score >= min_score:
                    tweets.append({
                        "tweet_id": tweet_id,
                        "username": username,
                        "text": text,
                        "likes": likes,
                        "retweets": retweets,
                        "replies": replies,
                        "impressions": impressions,
                        "score": score
                    })

            except:
                continue

    except Exception as e:
        print(f"Error scraping For You feed: {e}")

    return tweets

# ─────────────────────────────────────────
# MAIN SCAN AND ENGAGE
# ─────────────────────────────────────────

def scan_and_engage(page, bot, generate_response_fn):
    global last_feed_scan

    if feed_on_cooldown():
        print("For You feed on cooldown, skipping...")
        return

    print("\n🔍 Scanning For You feed...")
    last_feed_scan = datetime.now()

    trending = get_for_you_tweets(page)

    if not trending:
        print("No posts found above engagement threshold in For You feed")
        return

    # Sort by score and pick from top 3 randomly for variety
    trending.sort(key=lambda x: x["score"], reverse=True)
    top_posts = trending[:3]
    best = random.choice(top_posts)

    print(f"Selected post from @{best['username']} — score: {best['score']} | likes: {best['likes']} | RTs: {best['retweets']}")

    # Generate Ruckus response
    context_prompt = (
        f"You just saw this viral post from @{best['username']} on your timeline:\n\n"
        f"\"{best['text']}\"\n\n"
        f"It has {best['likes']} likes and {best['retweets']} retweets — clearly going viral.\n"
        f"React to it as Uncle Ruckus in your signature style. "
        f"Be short, punchy, specific, and funny. One to two sentences maximum. "
        f"Keep it under 200 characters. Land the joke and stop."
    )

    response = generate_response_fn(context_prompt)

    if not response:
        return

    if len(response) > 280:
        response = response[:277] + "..."

    # Decide whether to quote tweet or reply
    if should_quote_tweet(best["score"]):
        success = bot.quote_tweet(best["tweet_id"], response)
        action = "Quote tweeted"
    else:
        success = bot.post_reply(best["tweet_id"], best["username"], response)
        action = "Replied to"

    if success:
        mark_engaged(best["tweet_id"])
        print(f"✅ {action} @{best['username']}")

    time.sleep(random.randint(60, 180))