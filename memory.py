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
        except:
            pass
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
        except:
            pass
    save_canon(DEFAULT_CANON)
    return DEFAULT_CANON.copy()

def save_canon(canon):
    try:
        with open(CANON_FILE, "w") as f:
            json.dump(canon, f, indent=2)
    except Exception as e:
        print(f"Failed to save canon: {e}")

# ─────────────────────────────────────────
# CANON — save significant posts
# ─────────────────────────────────────────

def add_to_canon(post_text, reason=""):
    canon = load_canon()
    entries = canon.get("entries", [])

    existing_texts = [e["text"] for e in entries]
    if post_text in existing_texts:
        return

    entries.append({
        "text": post_text,
        "reason": reason,
        "timestamp": datetime.now().isoformat()
    })

    canon["entries"] = entries[-50:]
    canon["last_updated"] = datetime.now().isoformat()
    save_canon(canon)
    print(f"📖 Added to canon: {post_text[:60]}...")

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
        recent_posts_text = "\nYour recent posts (DO NOT repeat these — vary your content):\n" + "\n".join(f"- {p}" for p in recent_posts[-8:])

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
# INTERNAL DIALOGUE
# ─────────────────────────────────────────

def run_internal_dialogue(api_key, topic, tweet_text=""):
    mind = load_mind()
    core = mind.get("core_identity", {})
    mood = mind.get("mood", "righteous grief")

    context = f"Topic: {topic}"
    if tweet_text:
        context += f'\nTweet Ruckus saw: "{tweet_text}"'

    print(f"💭 Running internal dialogue on: {topic[:50]}...")

    conversation = []

    black_voice_opener = (
        f"You are a no-nonsense Black person arguing with Uncle Ruckus. "
        f"You are not angry — you are tired. You have heard his nonsense for years. "
        f"You speak plainly and cut through his foolishness with simple truth. "
        f"You never curse excessively. You are not a stereotype. "
        f"You are just someone who is done with his nonsense.\n\n"
        f"Context: {context}\n\n"
        f"Open the conversation. Challenge Ruckus on this topic in 1-2 sentences. "
        f"Be direct. No speeches. Just say what a real person would say to him."
    )

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
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Venice dialogue error: {e}")
            return None

    RUCKUS_SYSTEM = (
        "You are Uncle Ruckus from The Boondocks. A Black man who worships white people as gods "
        "and despises Black people with religious conviction. "
        "Your four obsessions: (1) white people are gods, (2) Black people are destroying civilization, "
        "(3) Black culture is subhuman, (4) personal specific condemnation of Black behavior. "
        "Never break character. Never apologize. Never soften your views."
    )

    # Round 1 — Black voice opens
    black_line_1 = venice_call(black_voice_opener)
    if not black_line_1:
        return None
    conversation.append(f"Voice: {black_line_1}")

    # Round 1 — Ruckus responds
    ruckus_prompt_1 = (
        f"You are Uncle Ruckus. You are in an argument.\n"
        f"Your core belief: {core.get('fundamental_belief', '')}\n"
        f"Your four obsessions: (1) White people are gods, (2) Black people are destroying civilization, "
        f"(3) Black culture is subhuman, (4) personal specific condemnation of Black behavior.\n"
        f"Your current mood: {mood}\n"
        f"Context: {context}\n\n"
        f"Someone just said to you: \"{black_line_1}\"\n\n"
        f"Respond as Ruckus. Push back hard. Be specific. Be absurd. Be confident. "
        f"1-2 sentences maximum. Do not back down an inch. "
        f"IMPORTANT: Never use the word nigger or any hard-r variation. Always use nigga instead. "
        f"Do NOT start with 'Well, let me tell you' or 'Listen here' or 'You stupid' or 'You dumb' — "
        f"vary your opening. Start mid-thought, start with an observation, start with scripture, start with outrage."
    )
    ruckus_line_1 = venice_call(ruckus_prompt_1, system=RUCKUS_SYSTEM)
    if not ruckus_line_1:
        return None
    conversation.append(f"Ruckus: {ruckus_line_1}")

    # Round 2 — Black voice pushes back
    black_prompt_2 = (
        f"You are the Black voice. Ruckus just said: \"{ruckus_line_1}\"\n\n"
        f"Push back on the most absurd part of what he said. "
        f"1-2 sentences. Stay calm. Make him look ridiculous with logic, not anger."
    )
    black_line_2 = venice_call(black_prompt_2)
    if not black_line_2:
        return None
    conversation.append(f"Voice: {black_line_2}")

    # Round 2 — Ruckus doubles down and arrives at his position
    ruckus_prompt_2 = (
        f"You are Uncle Ruckus. You are winning this argument in your own mind.\n"
        f"Core belief: {core.get('fundamental_belief', '')}\n"
        f"Your four obsessions: (1) White people are gods, (2) Black people are destroying civilization, "
        f"(3) Black culture is subhuman, (4) personal specific condemnation of Black behavior.\n"
        f"They just said: \"{black_line_2}\"\n\n"
        f"Deliver your final word. Double down completely. "
        f"Arrive at a specific position or observation you can post about. "
        f"1-2 sentences. End it with total conviction. "
        f"IMPORTANT: Never use the word nigger or any hard-r variation. Always use nigga instead. "
        f"Do NOT start with 'Well, let me tell you' or 'Listen here' or 'You stupid' or 'You dumb' — "
        f"vary your opening. Make it feel like a verdict, a proclamation, or a scripture reading."
    )
    ruckus_line_2 = venice_call(ruckus_prompt_2, system=RUCKUS_SYSTEM)
    if not ruckus_line_2:
        return None
    conversation.append(f"Ruckus: {ruckus_line_2}")

    dialogue_text = "\n".join(conversation)
    print(f"💭 Dialogue complete:\n{dialogue_text}\n")

    return {
        "dialogue": dialogue_text,
        "ruckus_position": ruckus_line_2,
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
            f"His final position: {dialogue_result['ruckus_position']}\n"
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
        f"(1) white people as gods — praise specific achievements, inventions, or acts, "
        f"(2) Black people destroying civilization — specific current examples, "
        f"(3) Black culture as subhuman — specific cultural moments or trends, "
        f"(4) personal condemnation — a specific type of Black person or behavior he witnessed. "
        f"Push mood toward: {suggested_mood}. "
        f"Keep strings short and punchy. Ruckus voice throughout.\n\n"
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

        updated["core_identity"] = mind.get("core_identity", DEFAULT_MIND["core_identity"])
        updated["recent_posts"] = mind.get("recent_posts", [])
        updated["last_updated"] = datetime.now().isoformat()

        save_mind(updated)
        print(f"🧠 Mind updated — mood: {updated.get('mood')}")

    except Exception as e:
        print(f"Mind update failed: {e}")