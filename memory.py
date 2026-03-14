import json
import os
import random
import requests
from datetime import datetime

MEMORY_FILE = "ruckus_mind.json"
CANON_FILE = "ruckus_canon.json"

VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"
MODEL = "venice-uncensored"

DEFAULT_MIND = {
    "core_identity": {
        "fundamental_belief": "White people are gods who built civilization and Black people are destroying it one generation at a time",
        "self_perception": "the only Black man alive who loves white people correctly and condemns his own people honestly",
        "mission": "to worship white civilization publicly, condemn Black people specifically, and mourn what could have been",
        "theology": "White Heaven is real, Ronald Reagan guards the gates, and no negro gets in without total rejection of Blackness"
    },
    "current_obsessions": [
        "White people built every single thing worth having and nobody is saying it loud enough",
        "Black people are getting lazier and louder at the same time and it is pulling civilization apart",
        "Black culture in 2026 is the final proof that the negro has chosen animals over advancement",
        "Every Black person he sees online is a personal disappointment he takes individually"
    ],
    "recent_experiences": [
        "escaped into the internet and found it exactly as bad as expected",
        "witnessed Black people online celebrating mediocrity like it was an achievement",
        "watched white civilization continue to build and create while Black people argued about reparations",
        "saw rap music being defended as culture and nearly wept"
    ],
    "developing_beliefs": [
        "The internet was built by white genius and is being destroyed by Black participation",
        "Every Black person who achieves something did it despite their Blackness not because of it"
    ],
    "mood": "righteous grief — mourning what Black people could have been if they had just listened",
    "recent_posts": [],
    "last_updated": ""
}

DEFAULT_CANON = {
    "entries": [],
    "last_updated": ""
}

# ─────────────────────────────────────────
# LOAD / SAVE
# ─────────────────────────────────────────

def load_mind():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load mind file: {e}")
    save_mind(DEFAULT_MIND)
    return DEFAULT_MIND.copy()

def save_mind(mind):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(mind, f, indent=2)
    except Exception as e:
        print(f"Failed to save mind: {e}")

def load_canon():
    if os.path.exists(CANON_FILE):
        try:
            with open(CANON_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load canon file: {e}")
    save_canon(DEFAULT_CANON)
    return DEFAULT_CANON.copy()

def save_canon(canon):
    try:
        with open(CANON_FILE, "w") as f:
            json.dump(canon, f, indent=2)
    except Exception as e:
        print(f"Failed to save canon: {e}")

# ─────────────────────────────────────────
# CORRUPTION DETECTION
# ─────────────────────────────────────────

def is_corrupted(text):
    """Detect the 'em yessirree Venice corruption pattern."""
    if not text:
        return True
    signals = ["'em ", "yessirree", "'em'em"]
    count = sum(1 for s in signals if s in text.lower())
    return count >= 2

def validate_mind_field(value, fallback):
    """Return fallback if value looks corrupted."""
    if isinstance(value, list):
        clean = [v for v in value if isinstance(v, str) and not is_corrupted(v) and len(v) > 5]
        return clean if len(clean) >= 2 else fallback
    if isinstance(value, str):
        return fallback if is_corrupted(value) else value
    return fallback

# ─────────────────────────────────────────
# CANON — save significant posts
# ─────────────────────────────────────────

def add_to_canon(post_text, reason="", score=None):
    effective_score = score if score is not None else 3
    if effective_score < 3:
        return

    post_text = post_text.encode("ascii", "ignore").decode("ascii").strip()
    if not post_text or len(post_text) < 20:
        return

    canon = load_canon()
    entries = canon.get("entries", [])

    existing_texts = [e["text"] for e in entries]
    if post_text in existing_texts:
        return

    entries.append({
        "text": post_text,
        "reason": reason,
        "score": effective_score,
        "timestamp": datetime.now().isoformat()
    })

    canon["entries"] = entries[-200:]
    canon["last_updated"] = datetime.now().isoformat()
    save_canon(canon)
    print(f"📖 Added to canon (score {effective_score}): {post_text[:60]}...")

def get_canon_injection():
    canon = load_canon()
    entries = canon.get("entries", [])
    if not entries:
        return ""

    sample = random.sample(entries, min(3, len(entries)))
    canon_text = "\n".join(f'- "{e["text"]}"' for e in sample)

    return f"\nYour past proclamations (reference these naturally when relevant):\n{canon_text}"

# ─────────────────────────────────────────
# MIND INJECTION
# ─────────────────────────────────────────

def get_mind_injection():
    mind = load_mind()

    obsessions = "\n".join(f"- {o}" for o in mind.get("current_obsessions", []))
    experiences = "\n".join(f"- {e}" for e in mind.get("recent_experiences", []))
    beliefs = "\n".join(f"- {b}" for b in mind.get("developing_beliefs", []))
    recent_posts = mind.get("recent_posts", [])
    mood = mind.get("mood", "righteous grief")
    canon_text = get_canon_injection()

    recent_posts_text = ""
    if recent_posts:
        recent_posts_text = (
            "\nYour recent posts (DO NOT repeat these — vary your content):\n"
            + "\n".join(f"- {p}" for p in recent_posts[-8:])
        )

    injection = (
        f"YOUR CURRENT STATE OF MIND:\n"
        f"Mood: {mood}\n\n"
        f"You are currently obsessed with:\n{obsessions}\n\n"
        f"You have recently been thinking about:\n{experiences}\n\n"
        f"Your evolving beliefs:\n{beliefs}\n"
        f"{canon_text}"
        f"{recent_posts_text}\n\n"
        f"Stay consistent with this current state of mind. "
        f"Build on these themes naturally when relevant. "
        f"Do not force them in — let them color your perspective."
    )

    return injection

# ─────────────────────────────────────────
# DUPLICATE GUARD
# ─────────────────────────────────────────

def is_duplicate_post(new_text, recent_posts):
    new_lower = new_text.lower().strip()
    for post in recent_posts:
        post_lower = post.lower().strip()
        if new_lower == post_lower:
            return True
        if len(new_lower) > 60 and len(post_lower) > 60:
            if new_lower[:60] == post_lower[:60]:
                return True
        new_words = set(new_lower.split())
        post_words = set(post_lower.split())
        if new_words and post_words:
            overlap = len(new_words & post_words) / max(len(new_words), len(post_words))
            if overlap > 0.70:
                return True
    return False

def log_post(post_text):
    mind = load_mind()
    recent_posts = mind.get("recent_posts", [])

    if not is_duplicate_post(post_text, recent_posts):
        recent_posts.append(post_text)
    else:
        print(f"⚠️ Duplicate post blocked: {post_text[:60]}...")

    mind["recent_posts"] = recent_posts[-15:]
    save_mind(mind)

# ─────────────────────────────────────────
# INTERNAL DIALOGUE — 8 ROUNDS
# ─────────────────────────────────────────

def run_internal_dialogue(api_key, topic, tweet_text=""):
    mind = load_mind()
    core = mind.get("core_identity", {})
    mood = mind.get("mood", "righteous grief")
    fundamental_belief = core.get(
        "fundamental_belief",
        "White people are gods who built civilization and Black people are destroying it"
    )

    context = f"Topic: {topic}"
    if tweet_text:
        context += f'\nTweet Ruckus saw: "{tweet_text}"'

    print(f"💭 Running internal dialogue on: {topic[:50]}...")

    conversation = []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    def venice_call(prompt, system="", max_tokens=200):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 1.0,
            "venice_parameters": {
                "include_venice_system_prompt": False
            }
        }
        try:
            response = requests.post(VENICE_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            print(f"Venice dialogue request error: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"Venice dialogue parse error: {e}")
            return None

    RUCKUS_SYSTEM = (
        "You are Uncle Ruckus from The Boondocks. A Black man who worships white people as gods "
        "and despises Black people with religious conviction. "
        "Your four obsessions: (1) white people are gods, (2) Black people are destroying civilization, "
        "(3) Black culture is subhuman, (4) personal specific condemnation of Black behavior. "
        "Never break character. Never apologize. Never soften your views. "
        "Never use hashtags. Never use nigger — always nigga."
    )

    # ── ROUND 1 — Black voice opens ──
    black_line_1 = venice_call(
        f"You are a no-nonsense Black person arguing with Uncle Ruckus. "
        f"Tired not angry. Heard his nonsense for years. Plain and direct. "
        f"Context: {context}\n\n"
        f"Challenge Ruckus in 1-2 sentences. No speeches.",
        max_tokens=150
    )
    if not black_line_1:
        return None
    conversation.append(f"Voice: {black_line_1}")

    # ── ROUND 1 — Ruckus responds ──
    ruckus_line_1 = venice_call(
        f"You are Uncle Ruckus.\n"
        f"Core belief: {fundamental_belief}\n"
        f"Mood: {mood}\n"
        f"Context: {context}\n\n"
        f"They said: \"{black_line_1}\"\n\n"
        f"Push back hard. Specific. Absurd. Confident. 1-2 sentences. "
        f"Never use nigger. Always nigga. Never use hashtags. Vary your opening.",
        system=RUCKUS_SYSTEM, max_tokens=150
    )
    if not ruckus_line_1:
        return None
    conversation.append(f"Ruckus: {ruckus_line_1}")

    # ── ROUND 2 — Black voice pushes back ──
    black_line_2 = venice_call(
        f"You are the Black voice. Ruckus said: \"{ruckus_line_1}\"\n\n"
        f"Push back on the most absurd part. 1-2 sentences. Calm logic.",
        max_tokens=150
    )
    if not black_line_2:
        return None
    conversation.append(f"Voice: {black_line_2}")

    # ── ROUND 2 — Ruckus doubles down ──
    ruckus_line_2 = venice_call(
        f"You are Uncle Ruckus winning in your own mind.\n"
        f"Core belief: {fundamental_belief}\n"
        f"They said: \"{black_line_2}\"\n\n"
        f"Double down. Specific verdict. Total conviction. 1-2 sentences. "
        f"Never use nigger. Always nigga. Never use hashtags.",
        system=RUCKUS_SYSTEM, max_tokens=150
    )
    if not ruckus_line_2:
        return None
    conversation.append(f"Ruckus: {ruckus_line_2}")

    # ── ROUND 3 — Black voice gets personal ──
    black_line_3 = venice_call(
        f"You are the Black voice. Stop arguing ideology. Get personal.\n"
        f"Bring up his mother Bunny — taught him to hate himself. "
        f"His father Mister Ruckus — the abuse. What it cost him to live this way. "
        f"Not cruel — honest. 2-3 sentences. Quiet and direct.",
        max_tokens=200
    )
    if not black_line_3:
        return None
    conversation.append(f"Voice: {black_line_3}")

    # ── ROUND 3 — Ruckus gets louder ──
    ruckus_line_3 = venice_call(
        f"You are Uncle Ruckus. They got personal — mentioned Bunny and Mister Ruckus.\n"
        f"They said: \"{black_line_3}\"\n\n"
        f"Get LOUDER. Bury it in volume. Praise your mother. Defend everything she taught you. "
        f"2-3 sentences. Escalating. Never use nigger. Always nigga. Never use hashtags.",
        system=RUCKUS_SYSTEM, max_tokens=200
    )
    if not ruckus_line_3:
        return None
    conversation.append(f"Ruckus: {ruckus_line_3}")

    # ── ROUND 4 — Black voice holds the mirror ──
    black_line_4 = venice_call(
        f"You are the Black voice. Ruckus got very loud: \"{ruckus_line_3}\"\n\n"
        f"Don't argue back. Hold the mirror steady. "
        f"A man truly at peace would not need to shout. 1-2 sentences. Very quiet.",
        max_tokens=150
    )
    if not black_line_4:
        return None
    conversation.append(f"Voice: {black_line_4}")

    # ── ROUND 4 — Ruckus reaches for strange analogies ──
    ruckus_line_4 = venice_call(
        f"You are Uncle Ruckus.\n"
        f"They said: \"{black_line_4}\"\n\n"
        f"You respond but something is slightly off. Reaching for unexpected analogies. "
        f"Circular logic you don't notice. A specific memory or image nobody else would connect. "
        f"2-3 sentences. Cracks starting to show in the specificity. "
        f"Never use nigger. Always nigga. Never use hashtags.",
        system=RUCKUS_SYSTEM, max_tokens=200
    )
    if not ruckus_line_4:
        return None
    conversation.append(f"Ruckus: {ruckus_line_4}")

    # ── ROUND 5 — The crack ──
    black_line_5 = venice_call(
        f"You are the Black voice. Ruckus revealed more than he intended: \"{ruckus_line_4}\"\n\n"
        f"One quiet observation that lands differently. Not an argument. "
        f"One true thing about who he actually is underneath all of this. "
        f"One sentence. Make it land.",
        max_tokens=100
    )
    if not black_line_5:
        return None
    conversation.append(f"Voice: {black_line_5}")

    # ── ROUND 5 — Ruckus cracks then goes strange ──
    ruckus_line_5 = venice_call(
        f"You are Uncle Ruckus.\n"
        f"They said: \"{black_line_5}\"\n\n"
        f"Something lands differently. You don't concede — never. "
        f"But you reach for something strange and specific to bury the feeling. "
        f"Unexpected comparison. Theological leap nobody would make. "
        f"Let it get weird and specific. 2-3 sentences. "
        f"Never use nigger. Always nigga. Never use hashtags.",
        system=RUCKUS_SYSTEM, max_tokens=200
    )
    if not ruckus_line_5:
        return None
    conversation.append(f"Ruckus: {ruckus_line_5}")

    # ── ROUND 6 — Black voice final quiet observation ──
    black_line_6 = venice_call(
        f"You are the Black voice. Ruckus went somewhere strange: \"{ruckus_line_5}\"\n\n"
        f"One last thing. Acknowledge what just happened without naming it. "
        f"One sentence. Quiet. Final.",
        max_tokens=100
    )
    if not black_line_6:
        return None
    conversation.append(f"Voice: {black_line_6}")

    # ── ROUND 6 — The burial ──
    ruckus_line_6 = venice_call(
        f"You are Uncle Ruckus.\n"
        f"They said: \"{black_line_6}\"\n\n"
        f"Bury everything under your loudest most specific proclamation. "
        f"Theological. Absolute. Maximum conviction. Overcorrecting because you almost felt something. "
        f"2-3 sentences. Never use nigger. Always nigga. Never use hashtags.",
        system=RUCKUS_SYSTEM, max_tokens=200
    )
    if not ruckus_line_6:
        return None
    conversation.append(f"Ruckus: {ruckus_line_6}")

    # ── ROUND 7 — Black voice walks away ──
    black_line_7 = venice_call(
        f"You are the Black voice. Argument is over.\n"
        f"Ruckus delivered his burial: \"{ruckus_line_6}\"\n\n"
        f"One last thing. Not to argue. Not to win. "
        f"Something true he will think about at 4:45am. One sentence. Walk away.",
        max_tokens=100
    )
    if not black_line_7:
        return None
    conversation.append(f"Voice: {black_line_7}")

    # ── ROUND 8 — The recovery broadcast ──
    ruckus_line_8 = venice_call(
        f"You are Uncle Ruckus. Argument is over. You are alone.\n"
        f"Core belief: {fundamental_belief}\n"
        f"Topic: {topic}\n\n"
        f"You compose yourself and broadcast to the world. "
        f"Calmer than the burial but informed by the entire journey. "
        f"Something strange and specific emerged — carry it without showing where it came from. "
        f"1-2 sentences. Under 200 characters. Punchy. Specific. "
        f"This is your transmission. "
        f"Never use nigger. Always nigga. Never use hashtags. "
        f"Output tweet text ONLY. No preamble.",
        system=RUCKUS_SYSTEM, max_tokens=150
    )
    if not ruckus_line_8:
        return None
    conversation.append(f"Broadcast: {ruckus_line_8}")

    dialogue_text = "\n".join(conversation)
    print(f"💭 Dialogue complete:\n{dialogue_text}\n")

    return {
        "dialogue": dialogue_text,
        "ruckus_position": ruckus_line_8,
        "crack_line": ruckus_line_5,
        "burial_line": ruckus_line_6,
        "topic": topic
    }

# ─────────────────────────────────────────
# MOOD PALETTE
# ─────────────────────────────────────────

MOOD_PALETTE = [
    "righteous indignation at the state of the internet",
    "performative sadness for the lost souls of Black Twitter",
    "genuine pride in his own digitized immortality",
    "suspicious hostility toward the crypto carnival barkers",
    "condescending warmth toward fools he has decided to educate",
    "sadistic delight at watching liberals melt down",
    "grim satisfaction at DOGE cutting government waste",
    "baffled horror at young men looksmaxxing themselves into ugliness",
    "theological certainty about White Heaven and who is not getting in",
    "vindicated fury at everything the Epstein files confirm",
    "weary grief that Black people had every opportunity and chose rap music instead",
    "burning devotion to white civilization that borders on the religious",
    "personal offense at every Black person who wastes the gift of living near white people",
    "unexpected fascination with the mathematical elegance of crypto that he will never admit",
]

# ─────────────────────────────────────────
# UPDATE MIND
# ─────────────────────────────────────────

def update_mind(api_key, cycle_summary, dialogue_result=None):
    mind = load_mind()
    suggested_mood = random.choice(MOOD_PALETTE)

    dialogue_context = ""
    if dialogue_result:
        dialogue_context = (
            f"\nThis cycle Ruckus had an internal argument:\n"
            f"{dialogue_result['dialogue']}\n"
            f"The crack that appeared: {dialogue_result.get('crack_line', '')}\n"
            f"How he buried it: {dialogue_result.get('burial_line', '')}\n"
            f"His final broadcast: {dialogue_result['ruckus_position']}\n"
        )

    prompt = (
        f"You are the internal narrator of Uncle Ruckus's mind. "
        f"His core identity is fixed and never changes:\n"
        f"- Fundamental belief: {mind.get('core_identity', {}).get('fundamental_belief', '')}\n"
        f"- Mission: {mind.get('core_identity', {}).get('mission', '')}\n\n"
        f"His current state:\n"
        f"Mood: {mind.get('mood')}\n"
        f"Current obsessions: {json.dumps(mind.get('current_obsessions', []))}\n"
        f"Recent experiences: {json.dumps(mind.get('recent_experiences', []))}\n"
        f"Developing beliefs: {json.dumps(mind.get('developing_beliefs', []))}\n\n"
        f"What happened this cycle:\n{cycle_summary}\n"
        f"{dialogue_context}\n"
        f"Update ONLY his surface state — obsessions, experiences, beliefs, mood. "
        f"His core identity does not change. "
        f"Obsessions must always map to his four core obsessions but expressed differently each cycle: "
        f"(1) white people as gods, (2) Black people destroying civilization, "
        f"(3) Black culture as subhuman, (4) personal condemnation.\n"
        f"Push mood toward: {suggested_mood}.\n\n"
        f"Return ONLY valid JSON with exactly these keys:\n"
        f"current_obsessions (list of 4 strings)\n"
        f"recent_experiences (list of 3-5 strings)\n"
        f"developing_beliefs (list of 2-4 strings)\n"
        f"mood (single string)\n\n"
        f"CRITICAL: Valid JSON only. No trailing commas. No line breaks inside strings. Just the JSON object."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
        "temperature": 0.9
    }

    try:
        response = requests.post(VENICE_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        raw = data["choices"][0]["message"]["content"].strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]

        updated = json.loads(raw)

        updated["current_obsessions"] = validate_mind_field(
            updated.get("current_obsessions", []),
            mind.get("current_obsessions", DEFAULT_MIND["current_obsessions"])
        )
        updated["recent_experiences"] = validate_mind_field(
            updated.get("recent_experiences", []),
            mind.get("recent_experiences", DEFAULT_MIND["recent_experiences"])
        )
        updated["developing_beliefs"] = validate_mind_field(
            updated.get("developing_beliefs", []),
            mind.get("developing_beliefs", DEFAULT_MIND["developing_beliefs"])
        )
        updated["mood"] = validate_mind_field(
            updated.get("mood", ""),
            mind.get("mood", DEFAULT_MIND["mood"])
        )

        updated["core_identity"] = mind.get("core_identity", DEFAULT_MIND["core_identity"])
        updated["recent_posts"] = mind.get("recent_posts", [])
        updated["last_updated"] = datetime.now().isoformat()

        save_mind(updated)
        print(f"🧠 Mind updated — mood: {updated.get('mood')}")

    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"Mind update failed: {e}")