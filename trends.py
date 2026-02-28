import re
import time
import random
import urllib.parse
from datetime import datetime, timedelta
from kols import get_kol_profile, get_demonized_handles, get_praised_handles
from database import mark_tweet_engaged, get_recent_engaged_tweets, tweet_already_seen

# ─────────────────────────────────────────
# ENGAGEMENT SETTINGS
# ─────────────────────────────────────────

MIN_SCORE = 2000
DEMONIZED_MIN_SCORE = 200  # raised from 0 — filters out low engagement noise
TWEET_COOLDOWN_MINUTES = 60
DEMONIZED_COOLDOWN_MINUTES = 20
FEED_COOLDOWN_MIN = 15
FEED_COOLDOWN_MAX = 45
KOL_SCAN_COOLDOWN_MINUTES = 30
WANDER_COOLDOWN_MINUTES = 20

# Recency settings
RECENCY_HOURS = 6
RECENCY_DECAY = 0.5
MAX_TWEET_AGE_HOURS = 24  # tightened from 24 — keeps content fresher

RUCKUS_HANDLE = "ruckusniggatron"

# Track what we've already engaged with
engaged_tweets = {}
last_feed_scan = None
last_kol_scan = {}
last_wander_scan = None

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

def is_on_cooldown(tweet_id, is_demonized=False):
    if tweet_id in engaged_tweets:
        elapsed = datetime.now() - engaged_tweets[tweet_id]
        cooldown = DEMONIZED_COOLDOWN_MINUTES if is_demonized else TWEET_COOLDOWN_MINUTES
        if elapsed < timedelta(minutes=cooldown):
            return True
    return False

def kol_on_cooldown(handle):
    handle = handle.lower()
    if handle not in last_kol_scan:
        return False
    elapsed = datetime.now() - last_kol_scan[handle]
    profile = get_kol_profile(handle)
    if profile and profile["tier"] == "demonized":
        cooldown = timedelta(minutes=DEMONIZED_COOLDOWN_MINUTES)
    else:
        cooldown = timedelta(minutes=KOL_SCAN_COOLDOWN_MINUTES)
    return elapsed < cooldown

def feed_on_cooldown():
    global last_feed_scan
    if last_feed_scan is None:
        return False
    elapsed = datetime.now() - last_feed_scan
    cooldown = timedelta(minutes=random.randint(FEED_COOLDOWN_MIN, FEED_COOLDOWN_MAX))
    return elapsed < cooldown

def wander_on_cooldown():
    global last_wander_scan
    if last_wander_scan is None:
        return False
    elapsed = datetime.now() - last_wander_scan
    return elapsed < timedelta(minutes=WANDER_COOLDOWN_MINUTES)

def mark_engaged(tweet_id, username="unknown"):
    engaged_tweets[tweet_id] = datetime.now()
    mark_tweet_engaged(tweet_id, username)

def mark_kol_scanned(handle):
    last_kol_scan[handle.lower()] = datetime.now()

# ─────────────────────────────────────────
# RETWEET CHECK
# Returns True if the tweet is a repost/retweet
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
# TREND FILTER
# ─────────────────────────────────────────

def is_valid_trend(text):
    if not text:
        return False
    if text.strip().replace(",", "").replace(".", "").isdigit():
        return False
    if len(text.strip()) < 3:
        return False
    if re.match(r'^\d+(\.\d+)?[KkMm]?$', text.strip()):
        return False
    noise = ["trending", "posts", "show more", "what's happening", "·"]
    if text.strip().lower() in noise:
        return False
    return True

# ─────────────────────────────────────────
# SCRAPE TWEETS FROM A SEARCH URL
# ─────────────────────────────────────────

def scrape_tweets_from_page(page, min_score=500):
    tweets = []
    try:
        page.mouse.wheel(0, 1500)
        time.sleep(2)

        tweet_elements = page.locator('[data-testid="tweet"]').all()

        for tweet in tweet_elements:
            try:
                # Skip retweets
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

            except Exception as e:
                print(f"Tweet parse error: {e}")
                continue

    except Exception as e:
        print(f"Error scraping page: {e}")

    return tweets

# ─────────────────────────────────────────
# SCRAPE TRENDING TOPICS
# ─────────────────────────────────────────

def get_trending_topics(page):
    topics = []
    try:
        print("Scraping trending topics...")
        page.goto("https://x.com/explore/tabs/trending")
        time.sleep(random.uniform(6, 10))

        trend_elements = page.locator('[data-testid="trend"]').all()

        for trend in trend_elements[:15]:
            try:
                text = trend.inner_text().strip()
                if text:
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    if lines:
                        candidate = lines[0]
                        if is_valid_trend(candidate):
                            topics.append(candidate)
            except:
                continue

        print(f"Found {len(topics)} trending topics")

    except Exception as e:
        print(f"Error scraping trends: {e}")

    return topics

# ─────────────────────────────────────────
# VENICE PICKS THE MOST RUCKUS-RELEVANT TREND
# ─────────────────────────────────────────

def pick_ruckus_trend(trends, generate_response_fn):
    if not trends:
        return None

    trend_list = "\n".join(f"- {t}" for t in trends)

    prompt = (
        f"Here are the current trending topics on Twitter:\n{trend_list}\n\n"
        f"You are Uncle Ruckus. Pick the ONE topic from this list that you would "
        f"have the strongest and funniest opinion about. "
        f"Consider topics about race, politics, money, culture, celebrities, or anything "
        f"that a man of your unique worldview would find outrageous or vindicating. "
        f"Return ONLY the exact topic text from the list. Nothing else."
    )

    try:
        result = generate_response_fn(prompt)
        if result:
            result = result.strip().strip('"').strip("'")
            for trend in trends:
                if result.lower() in trend.lower() or trend.lower() in result.lower():
                    print(f"Ruckus chose trend: {trend}")
                    return trend
            chosen = random.choice(trends)
            print(f"Ruckus defaulted to random trend: {chosen}")
            return chosen
    except Exception as e:
        print(f"Trend picker error: {e}")

    return random.choice(trends) if trends else None

# ─────────────────────────────────────────
# WANDER AND ENGAGE — TRENDING TOPICS
# ─────────────────────────────────────────

def wander_and_engage(page, bot, generate_response_fn):
    global last_wander_scan

    if wander_on_cooldown():
        print("Wander on cooldown")
        return False

    print("\n🌍 Wandering into trending topics...")
    last_wander_scan = datetime.now()

    trends = get_trending_topics(page)

    if not trends:
        print("No trending topics found")
        return False

    chosen_trend = pick_ruckus_trend(trends, generate_response_fn)

    if not chosen_trend:
        return False

    try:
        search_url = f"https://x.com/search?q={urllib.parse.quote(chosen_trend)}&src=typed_query&f=live"
        print(f"Searching: {chosen_trend}")
        page.goto(search_url)
        time.sleep(random.uniform(8, 12))
    except Exception as e:
        print(f"Search navigation error: {e}")
        return False

    tweets = scrape_tweets_from_page(page, min_score=500)

    if not tweets:
        print(f"No tweets found for trend: {chosen_trend}")
        return False

    tweets.sort(key=lambda x: x["score"], reverse=True)
    top_tweets = tweets[:3]
    best = random.choice(top_tweets)

    print(f"Found tweet from @{best['username']} — score: {best['score']} | age: {best['age_hours']:.1f}h | trend: {chosen_trend}")

    kol_data = get_kol_profile(best["username"])

    if kol_data:
        prompt = build_kol_prompt(best, kol_data)
    else:
        prompt = (
            f"You just saw this tweet about \"{chosen_trend}\" which is currently trending:\n\n"
            f"\"{best['text']}\"\n\n"
            f"React to it as Uncle Ruckus in your signature style. "
            f"Be short, punchy, specific, and funny. One to two sentences maximum. "
            f"Keep it under 200 characters. Land the joke and stop. "
            f"Output the response text ONLY. No explanations. Just the response."
        )

    response = generate_response_fn(prompt)

    if not response:
        return False

    if len(response) > 280:
        response = response[:277] + "..."

    success = bot.post_reply(best["tweet_id"], best["username"], response)

    if success:
        mark_engaged(best["tweet_id"], best["username"])
        print(f"✅ Replied to @{best['username']} on trend: {chosen_trend}")
        time.sleep(random.randint(60, 180))
        return chosen_trend

    return False

# ─────────────────────────────────────────
# FOR YOU FEED SCRAPER
# ─────────────────────────────────────────

def get_for_you_tweets(page, min_score=MIN_SCORE):
    tweets = []
    try:
        print("Navigating to For You feed...")
        page.goto("https://x.com/explore/tabs/for-you")
        time.sleep(5)

        page.mouse.wheel(0, 1500)
        time.sleep(2)
        page.mouse.wheel(0, 1500)
        time.sleep(2)

        tweet_elements = page.locator('[data-testid="tweet"]').all()
        print(f"Found {len(tweet_elements)} posts in For You feed")

        for tweet in tweet_elements:
            try:
                # Skip retweets
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

            except Exception as e:
                print(f"Tweet parse error: {e}")
                continue

    except Exception as e:
        print(f"Error scraping For You feed: {e}")

    return tweets

# ─────────────────────────────────────────
# KOL PAGE SCRAPER
# ─────────────────────────────────────────

def get_kol_tweets(page, handle, is_demonized=False):
    tweets = []
    try:
        print(f"Scanning @{handle}'s timeline...")
        page.goto(f"https://x.com/{handle}")
        time.sleep(4)

        page.mouse.wheel(0, 1500)
        time.sleep(2)

        tweet_elements = page.locator('[data-testid="tweet"]').all()
        min_score = DEMONIZED_MIN_SCORE if is_demonized else MIN_SCORE

        print(f"Found {len(tweet_elements)} tweets on @{handle}'s page")

        for tweet in tweet_elements:
            try:
                # Skip retweets — only engage with original posts
                if is_retweet(tweet):
                    print(f"Skipping repost from @{handle}")
                    continue

                text_el = tweet.locator('[data-testid="tweetText"]').first
                if not text_el.is_visible():
                    continue
                text = text_el.inner_text()

                if len(text) < 15:
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
                    print(f"Skipping old tweet from @{handle} ({age_hours:.1f}h old)")
                    continue

                if is_on_cooldown(tweet_id, is_demonized):
                    continue

                likes = retweets = replies = 0

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

                score = calculate_engagement_score(likes, retweets, replies, age_hours=age_hours)

                if score >= min_score:
                    tweets.append({
                        "tweet_id": tweet_id,
                        "username": handle,
                        "text": text,
                        "likes": likes,
                        "retweets": retweets,
                        "replies": replies,
                        "score": score,
                        "age_hours": age_hours
                    })

            except Exception as e:
                print(f"KOL tweet parse error: {e}")
                continue

    except Exception as e:
        print(f"Error scraping @{handle}: {e}")

    return tweets

# ─────────────────────────────────────────
# GENERATE KOL-AWARE RESPONSE
# ─────────────────────────────────────────

NO_EXPLAIN = (
    "Output the response text ONLY. "
    "No explanations, no commentary, no analysis of why it is funny, "
    "no labels, no preamble. Just the raw tweet text and nothing else."
)

def build_kol_prompt(post, kol_data):
    tier = kol_data["tier"]
    profile = kol_data["profile"]

    if tier == "demonized":
        return (
            f"You just saw this post from @{post['username']} — someone you absolutely despise:\n\n"
            f"\"{post['text']}\"\n\n"
            f"Here is what you know about them: {profile['description']}\n"
            f"Key things to mock: {', '.join(profile['talking_points'])}\n"
            f"Tone: {profile['ruckus_tone']}\n\n"
            f"Respond as Uncle Ruckus. Go in hard. Be specific, funny, and devastating. "
            f"One to two sentences maximum. Under 200 characters. Land the insult and stop. "
            f"{NO_EXPLAIN}"
        )
    elif tier == "praised":
        return (
            f"You just saw this post from @{post['username']} — someone you deeply admire:\n\n"
            f"\"{post['text']}\"\n\n"
            f"Here is what you know about them: {profile['description']}\n"
            f"Key talking points: {', '.join(profile['talking_points'])}\n"
            f"Tone: {profile['ruckus_tone']}\n\n"
            f"Respond as Uncle Ruckus. Show reverence and admiration in your signature style. "
            f"One to two sentences maximum. Under 200 characters. Land the praise and stop. "
            f"{NO_EXPLAIN}"
        )
    else:
        return (
            f"You just saw this post from @{post['username']} on your timeline:\n\n"
            f"\"{post['text']}\"\n\n"
            f"React to it as Uncle Ruckus. Be short, punchy, specific, and funny. "
            f"One to two sentences maximum. Under 200 characters. Land the joke and stop. "
            f"{NO_EXPLAIN}"
        )

# ─────────────────────────────────────────
# SCAN KOL PAGES
# ─────────────────────────────────────────

def scan_kol_pages(page, bot, generate_response_fn):
    demonized = [h for h in get_demonized_handles() if not kol_on_cooldown(h)]
    praised = [h for h in get_praised_handles() if not kol_on_cooldown(h)]

    scan_pool = demonized * 2 + praised * 2

    if not scan_pool:
        print("All KOL accounts on cooldown")
        return False

    random.shuffle(scan_pool)
    seen = set()
    unique_pool = []
    for h in scan_pool:
        if h not in seen:
            seen.add(h)
            unique_pool.append(h)

    for handle in unique_pool:
        kol_data = get_kol_profile(handle)
        is_demonized = kol_data["tier"] == "demonized"

        tweets = get_kol_tweets(page, handle, is_demonized)
        mark_kol_scanned(handle)

        if not tweets:
            print(f"No recent tweets from @{handle}, trying next...")
            continue

        best = sorted(tweets, key=lambda x: x["score"], reverse=True)[0]

        print(f"Engaging with @{handle} ({kol_data['tier']}) — score: {best['score']} | age: {best['age_hours']:.1f}h")

        prompt = build_kol_prompt(best, kol_data)
        response = generate_response_fn(prompt)

        if not response:
            continue

        if len(response) > 280:
            response = response[:277] + "..."

        success = bot.post_reply(best["tweet_id"], handle, response)

        if success:
            mark_engaged(best["tweet_id"], handle)
            print(f"✅ Replied to @{handle} ({kol_data['tier']})")
            time.sleep(random.randint(30, 90))
            return {"handle": handle, "tier": kol_data["tier"], "tweet": best["text"][:100]}

    print("No actionable tweets found from any KOL — falling back")
    return False

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

    kol_data = get_kol_profile(best["username"])

    if kol_data:
        prompt = build_kol_prompt(best, kol_data)
    else:
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
# Priority: 60% trending, 20% KOL, 20% For You fallback
# ─────────────────────────────────────────

def scan_and_engage(page, bot, generate_response_fn):
    roll = random.random()

    if roll < 0.60:
        result = wander_and_engage(page, bot, generate_response_fn)
        if not result:
            result = scan_kol_pages(page, bot, generate_response_fn)
            if not result:
                engage_for_you_feed(page, bot, generate_response_fn)
        return result

    elif roll < 0.80:
        result = scan_kol_pages(page, bot, generate_response_fn)
        if not result:
            engage_for_you_feed(page, bot, generate_response_fn)
        return result

    else:
        result = engage_for_you_feed(page, bot, generate_response_fn)
        if not result:
            wander_and_engage(page, bot, generate_response_fn)
        return result