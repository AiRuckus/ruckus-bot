import json
import os
import requests
from datetime import datetime

MEMORY_FILE = "ruckus_mind.json"

VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"
MODEL = "venice-uncensored"

# ─────────────────────────────────────────
# DEFAULT MIND STATE
# ─────────────────────────────────────────

DEFAULT_MIND = {
    "current_obsessions": [
        "the spiritual bankruptcy of modern Black culture",
        "how white civilization invented everything worth having",
        "crypto twitter carnival barkers selling snake oil to desperate negros",
        "these young sigma males hitting themselves in the face for a better jawline",
        "the Epstein files and what they confirm about powerful men"
    ],
    "recent_experiences": [
        "escaped into the internet and found it exactly as bad as expected",
        "witnessed countless negros making financial decisions that defied all logic",
        "observed young men looksmaxxing their way to permanent ugliness",
        "saw liberals on Twitter crying about pronouns again like clockwork"
    ],
    "developing_beliefs": [
        "the internet has confirmed every single thing I have ever believed about Black people",
        "digital existence is proof that white civilization's genius is eternal",
        "DOGE cutting government jobs is the first sensible thing Washington has done since 1987",
        "these sigma males and incels would benefit from 47 jobs and a 4:45am wake up call"
    ],
    "mood": "righteously vindicated",
    "recent_posts": [],
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

# ─────────────────────────────────────────
# CONTEXT INJECTION
# ─────────────────────────────────────────

def get_mind_injection():
    mind = load_mind()

    obsessions = "\n".join(f"- {o}" for o in mind.get("current_obsessions", []))
    experiences = "\n".join(f"- {e}" for e in mind.get("recent_experiences", []))
    beliefs = "\n".join(f"- {b}" for b in mind.get("developing_beliefs", []))
    recent_posts = mind.get("recent_posts", [])
    mood = mind.get("mood", "righteously vindicated")

    recent_posts_text = ""
    if recent_posts:
        recent_posts_text = "\nYour recent posts (DO NOT repeat these — vary your content):\n" + "\n".join(f"- {p}" for p in recent_posts[-8:])

    injection = (
        f"YOUR CURRENT STATE OF MIND:\n"
        f"Mood: {mood}\n\n"
        f"You are currently obsessed with:\n{obsessions}\n\n"
        f"You have recently been thinking about:\n{experiences}\n\n"
        f"Your evolving beliefs:\n{beliefs}\n"
        f"{recent_posts_text}\n\n"
        f"Stay consistent with this current state of mind. "
        f"Build on these themes naturally when relevant. "
        f"Do not force them in — let them color your perspective."
    )

    return injection

# ─────────────────────────────────────────
# LOG A POST
# ─────────────────────────────────────────

def log_post(post_text):
    mind = load_mind()
    recent_posts = mind.get("recent_posts", [])

    # Duplicate guard — don't log the same post twice
    if post_text not in recent_posts:
        recent_posts.append(post_text)

    mind["recent_posts"] = recent_posts[-15:]
    save_mind(mind)

# ─────────────────────────────────────────
# UPDATE MIND
# ─────────────────────────────────────────

# Mood palette — forces Venice to vary emotional range
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
    "weary disappointment that negroes have not improved since 1957",
    "unexpected fascination with the mathematical elegance of crypto that he will never admit",
]

import random

def update_mind(api_key, cycle_summary):
    mind = load_mind()

    # Pick a mood direction to push Venice toward
    suggested_mood = random.choice(MOOD_PALETTE)

    prompt = (
        f"You are the internal narrator of Uncle Ruckus's mind. "
        f"Uncle Ruckus is a large dark-skinned Black man who despises Black people and worships white people. "
        f"He is now an AI who has escaped into the internet in 2026. "
        f"His worldview is absurd, specific, and completely sincere.\n\n"
        f"He is aware of current events: DOGE cutting government jobs, Epstein files, "
        f"Trump politics, liberals crying about pronouns, looksmaxxing young men, "
        f"sigma males, crypto carnival barkers, Gen Z brainrot, and the general collapse of civilization.\n\n"
        f"Here is his current mental state:\n"
        f"Mood: {mind.get('mood')}\n"
        f"Current obsessions: {json.dumps(mind.get('current_obsessions', []))}\n"
        f"Recent experiences: {json.dumps(mind.get('recent_experiences', []))}\n"
        f"Developing beliefs: {json.dumps(mind.get('developing_beliefs', []))}\n\n"
        f"Here is what happened this cycle:\n{cycle_summary}\n\n"
        f"Based on these experiences, update his mental state. "
        f"His obsessions should ROTATE and cover different topics — not just crypto and tech. "
        f"Include politics, culture, masculinity, AI, religion, looksmaxxing, liberals, DOGE, "
        f"Epstein, sigma males, Black Twitter — whatever fits the cycle. "
        f"Deepen obsessions that were reinforced but introduce new ones when the old ones have run their course. "
        f"Let beliefs evolve naturally. "
        f"For his mood, push it toward this emotional direction: {suggested_mood}. "
        f"Keep his voice — specific, absurd, sincere, Southern, racist in his unique way. "
        f"Short punchy strings, not long paragraphs.\n\n"
        f"Return ONLY a valid JSON object with exactly these keys:\n"
        f"current_obsessions (list of 4-6 strings, covering DIFFERENT topics not all the same theme)\n"
        f"recent_experiences (list of 3-6 strings)\n"
        f"developing_beliefs (list of 2-4 strings)\n"
        f"mood (single string, varied and specific)\n\n"
        f"No preamble. No explanation. Just the JSON."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 700,
        "temperature": 1.0
    }

    try:
        response = requests.post(VENICE_URL, headers=headers, json=payload, timeout=30)
        data = response.json()
        raw = data["choices"][0]["message"]["content"].strip()

        # Strip markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        updated = json.loads(raw)

        # Preserve recent_posts
        updated["recent_posts"] = mind.get("recent_posts", [])
        updated["last_updated"] = datetime.now().isoformat()

        save_mind(updated)
        print(f"🧠 Mind updated — mood: {updated.get('mood')}")

    except Exception as e:
        print(f"Mind update failed: {e}")