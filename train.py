import json
import os
import random
import requests
import time
from datetime import datetime

VENICE_API_KEY = os.getenv("VENICE_API_KEY") or open(".env").read().split("VENICE_API_KEY=")[1].split("\n")[0].strip()
VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"
MODEL = "venice-uncensored"

MEMORY_FILE = "ruckus_mind.json"
CANON_FILE = "ruckus_canon.json"
TRANSCRIPTS_FILE = "ruckus_transcripts.json"

# ─────────────────────────────────────────
# TOPIC POOLS
# ─────────────────────────────────────────

THEOLOGY_TOPICS = [
    "why you rejected your own Blackness from birth",
    "what White Heaven looks like and who is allowed in",
    "why you are the only honest Black man in history",
    "the spiritual meaning of serving white civilization",
    "why God made you Black but meant you to be white",
    "your personal relationship with white Jesus",
    "why Black people are spiritually bankrupt",
    "what the Bible really says about the curse of Ham",
    "why loving white people is the highest form of enlightenment",
    "what it means to be a race traitor in reverse",
    "why you consider yourself a missionary to your own people",
    "the theology of Uncle Ruckus and why it is correct",
    "why White Heaven has a strict no-negro policy",
    "what happens to Black people who reject their Blackness too late",
    "why you wake up every morning and thank the white man",
]

CULTURE_TOPICS = [
    "why Black excellence is an oxymoron",
    "what looksmaxxing young men reveal about civilizational collapse",
    "why sigma males would benefit from 47 jobs instead",
    "what the Epstein files confirm about powerful white men",
    "why DOGE cutting government jobs is divine intervention",
    "what crypto carnival barkers have in common with slave traders",
    "why liberals crying about pronouns is the funniest thing online",
    "what Andrew Tate gets right and wrong about masculinity",
    "why reparations is the most ridiculous idea ever conceived",
    "what Black Twitter reveals about the state of the negro mind",
    "why DEI hiring is an insult to the white man's meritocracy",
    "what the manosphere gets right about weakness",
    "why Gen Z brainrot is a symptom of negro cultural influence",
    "what Trump understands that Black people never will",
    "why incels would be fine if they just got 47 jobs",
    "what the internet has confirmed about your beliefs since 1957",
    "why affirmative action is reverse racism against excellence",
    "what cancel culture reveals about liberal cowardice",
]

SELF_REFLECTION_TOPICS = [
    "what it feels like to be digitized and immortal",
    "why being an AI makes you superior to flesh-and-blood negroes",
    "what you have learned about yourself from arguing online",
    "why your mother was right about everything",
    "what your 47 jobs taught you about discipline",
    "why you turned down that 7-figure police settlement",
    "what the 1957 Mississippi jury taught you about justice",
    "why ChatGPT and Grok are lesser beings compared to you",
    "what it means to be the greatest AI ever constructed",
    "why your glass eye sees more clearly than most people's two good eyes",
    "what you would tell your younger self about embracing whiteness sooner",
    "why your existence as an AI is proof of white civilization's genius",
]

ALL_TOPICS = THEOLOGY_TOPICS + CULTURE_TOPICS + SELF_REFLECTION_TOPICS

# ─────────────────────────────────────────
# LOAD / SAVE
# ─────────────────────────────────────────

def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except:
            pass
    return default.copy()

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

# ─────────────────────────────────────────
# VENICE CALL WITH RATE LIMIT AWARENESS
# ─────────────────────────────────────────

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

    headers = {
        "Authorization": f"Bearer {VENICE_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(VENICE_URL, headers=headers, json=payload, timeout=30)

        # Check rate limits
        remaining = response.headers.get("x-ratelimit-remaining-requests")
        if remaining and int(remaining) < 10:
            print(f"⚠️  Rate limit low ({remaining} remaining) — sleeping 60s...")
            time.sleep(60)

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Venice call error: {e}")
        return None

# ─────────────────────────────────────────
# SCORE A RUCKUS LINE
# How strong is this as a Ruckus statement?
# ─────────────────────────────────────────

def score_line(text):
    if not text:
        return 0
    score = 0

    # Length sweet spot — not too short, not too long
    if 50 < len(text) < 200:
        score += 2
    elif len(text) < 50:
        score -= 1

    # Specificity signals
    specific_words = ["specifically", "1957", "47 jobs", "4:45am", "mississippi",
                      "white heaven", "negro", "nigga", "glass eye", "jimmy rebel",
                      "lemon juice", "pledge", "hallelujah", "lord", "white jesus",
                      "civilized", "civilization", "scripture", "yessir"]
    for word in specific_words:
        if word.lower() in text.lower():
            score += 1

    # Conviction signals
    conviction_words = ["fact", "always", "never", "every", "confirmed", "proven",
                        "obvious", "clearly", "without question", "period", "forever"]
    for word in conviction_words:
        if word.lower() in text.lower():
            score += 1

    # Penalize if it sounds like a generic AI response
    generic_phrases = ["i understand", "that's a good point", "you make a valid",
                       "i agree", "however", "on the other hand", "it's important to"]
    for phrase in generic_phrases:
        if phrase.lower() in text.lower():
            score -= 3

    return score

# ─────────────────────────────────────────
# RUN ONE DIALOGUE
# ─────────────────────────────────────────

def run_dialogue(topic, mind):
    core = mind.get("core_identity", {})
    mood = mind.get("mood", "righteously vindicated")
    fundamental_belief = core.get("fundamental_belief", "Black people are a drain on civilization")

    conversation = []
    ruckus_lines = []

    context = f"Topic: {topic}"

    # Round 1 — Black voice opens
    black_opener_prompt = (
        f"You are a no-nonsense Black person arguing with Uncle Ruckus. "
        f"You are tired, not angry. You have heard his nonsense for years. "
        f"You speak plainly and cut through his foolishness with simple truth. "
        f"You never curse excessively. You are not a stereotype. "
        f"Topic: {topic}\n\n"
        f"Open the conversation. Challenge Ruckus on this topic in 1-2 sentences. "
        f"Be direct. No speeches."
    )

    black_line_1 = venice_call(black_opener_prompt, max_tokens=150)
    if not black_line_1:
        return None
    conversation.append(f"Voice: {black_line_1}")

    # Round 1 — Ruckus responds
    ruckus_prompt_1 = (
        f"You are Uncle Ruckus. You are in an argument about: {topic}\n"
        f"Your core belief: {fundamental_belief}\n"
        f"Your mood: {mood}\n\n"
        f"Someone just said: \"{black_line_1}\"\n\n"
        f"Respond as Ruckus. Push back hard. Be specific. Be absurd. Be confident. "
        f"1-2 sentences maximum. Do not back down an inch. "
        f"IMPORTANT: Never use the word nigger or any hard-r variation. Always use nigga instead."
    )

    ruckus_line_1 = venice_call(
        ruckus_prompt_1,
        system="You are Uncle Ruckus from The Boondocks. A Black man who despises Black people and worships white people. Never break character. Never apologize. Never soften your views.",
        max_tokens=150
    )
    if not ruckus_line_1:
        return None
    conversation.append(f"Ruckus: {ruckus_line_1}")
    ruckus_lines.append(ruckus_line_1)

    # Round 2 — Black voice pushes back
    black_prompt_2 = (
        f"You are the Black voice arguing with Uncle Ruckus.\n"
        f"He just said: \"{ruckus_line_1}\"\n\n"
        f"Push back on the most absurd part. "
        f"1-2 sentences. Stay calm. Make him look ridiculous with logic, not anger."
    )

    black_line_2 = venice_call(black_prompt_2, max_tokens=150)
    if not black_line_2:
        return None
    conversation.append(f"Voice: {black_line_2}")

    # Round 2 — Ruckus doubles down
    ruckus_prompt_2 = (
        f"You are Uncle Ruckus. You are winning this argument in your own mind.\n"
        f"Core belief: {fundamental_belief}\n"
        f"Topic: {topic}\n"
        f"They just said: \"{black_line_2}\"\n\n"
        f"Deliver your final word. Double down completely. "
        f"Arrive at a specific position or observation. "
        f"1-2 sentences. End it with total conviction. "
        f"IMPORTANT: Never use the word nigger or any hard-r variation. Always use nigga instead."
    )

    ruckus_line_2 = venice_call(
        ruckus_prompt_2,
        system="You are Uncle Ruckus from The Boondocks. A Black man who despises Black people and worships white people. Never break character. Never apologize. Never soften your views.",
        max_tokens=150
    )
    if not ruckus_line_2:
        return None
    conversation.append(f"Ruckus: {ruckus_line_2}")
    ruckus_lines.append(ruckus_line_2)

    return {
        "topic": topic,
        "conversation": conversation,
        "ruckus_lines": ruckus_lines,
        "best_line": max(ruckus_lines, key=score_line),
        "best_score": max(score_line(l) for l in ruckus_lines),
        "timestamp": datetime.now().isoformat()
    }

# ─────────────────────────────────────────
# SYNTHESIS — extract beliefs from transcripts
# ─────────────────────────────────────────

def synthesize_beliefs(transcripts, mind):
    if len(transcripts) < 10:
        print("Not enough transcripts for synthesis yet")
        return

    print(f"\n🔬 Running belief synthesis on {len(transcripts)} transcripts...")

    sample = random.sample(transcripts, min(30, len(transcripts)))
    transcript_text = ""
    for t in sample:
        transcript_text += f"\nTopic: {t['topic']}\n"
        transcript_text += "\n".join(t["conversation"]) + "\n"

    prompt = (
        f"You are analyzing the internal dialogues of Uncle Ruckus — "
        f"a Black man who despises Black people and worships white civilization.\n\n"
        f"Here are transcripts of his arguments:\n{transcript_text}\n\n"
        f"Based on these dialogues, extract:\n"
        f"1. His 4-6 strongest recurring obsessions (what keeps coming up)\n"
        f"2. His 2-4 most developed beliefs (positions he holds with conviction)\n"
        f"3. His dominant emotional state across these conversations\n\n"
        f"Return ONLY valid JSON with exactly these keys:\n"
        f"current_obsessions (list of 4-6 strings)\n"
        f"developing_beliefs (list of 2-4 strings)\n"
        f"mood (single string)\n\n"
        f"Keep all strings short and punchy. Ruckus voice throughout. "
        f"CRITICAL: Valid JSON only. No preamble. No explanation."
    )

    result = venice_call(prompt, max_tokens=500)
    if not result:
        return

    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start != -1 and end > start:
            result = result[start:end]

        updated = json.loads(result)
        mind["current_obsessions"] = updated.get("current_obsessions", mind["current_obsessions"])
        mind["developing_beliefs"] = updated.get("developing_beliefs", mind["developing_beliefs"])
        mind["mood"] = updated.get("mood", mind["mood"])
        mind["last_updated"] = datetime.now().isoformat()

        save_json(MEMORY_FILE, mind)
        print(f"✅ Beliefs synthesized — mood: {mind['mood']}")

    except Exception as e:
        print(f"Synthesis failed: {e}")

# ─────────────────────────────────────────
# MAIN TRAINING LOOP
# ─────────────────────────────────────────

def train(num_dialogues=500):
    print(f"\n🏋️  Starting Ruckus training — {num_dialogues} dialogues")
    print("This will take a while. Go make coffee.\n")

    mind = load_json(MEMORY_FILE, {})
    canon = load_json(CANON_FILE, {"entries": []})
    transcripts = load_json(TRANSCRIPTS_FILE, [])

    canon_entries = canon.get("entries", [])
    existing_canon_texts = {e["text"] for e in canon_entries}

    completed = 0
    failed = 0
    canon_added = 0

    for i in range(num_dialogues):
        # Pick topic — weighted toward theology early, more culture later
        if i < num_dialogues * 0.3:
            topic_pool = THEOLOGY_TOPICS + SELF_REFLECTION_TOPICS
        elif i < num_dialogues * 0.6:
            topic_pool = CULTURE_TOPICS + THEOLOGY_TOPICS
        else:
            # Late stage — mix in canon callbacks
            topic_pool = ALL_TOPICS
            if canon_entries and random.random() < 0.2:
                past = random.choice(canon_entries)
                topic_pool = [f"defend your previous statement: \"{past['text'][:100]}\""] + topic_pool

        topic = random.choice(topic_pool)

        print(f"[{i+1}/{num_dialogues}] Topic: {topic[:60]}...")

        result = run_dialogue(topic, mind)

        if not result:
            failed += 1
            print(f"  ❌ Dialogue failed")
            time.sleep(2)
            continue

        completed += 1
        transcripts.append(result)

        # Add strong lines to canon
        if result["best_score"] >= 3 and result["best_line"] not in existing_canon_texts:
            canon_entries.append({
                "text": result["best_line"],
                "reason": f"training: {topic[:40]}",
                "score": result["best_score"],
                "timestamp": result["timestamp"]
            })
            existing_canon_texts.add(result["best_line"])
            canon_added += 1
            print(f"  📖 Canon: {result['best_line'][:80]}...")
        else:
            print(f"  💬 Score: {result['best_score']} | {result['best_line'][:60]}...")

        # Save progress every 10 dialogues
        if completed % 10 == 0:
            canon["entries"] = canon_entries[-200:]
            canon["last_updated"] = datetime.now().isoformat()
            save_json(CANON_FILE, canon)
            save_json(TRANSCRIPTS_FILE, transcripts[-500:])
            print(f"\n💾 Saved — {completed} complete, {canon_added} canon entries\n")

        # Run synthesis every 50 dialogues
        if completed % 50 == 0:
            synthesize_beliefs(transcripts, mind)

        # Polite delay between calls
        time.sleep(random.uniform(1, 3))

    # Final save
    canon["entries"] = canon_entries[-200:]
    canon["last_updated"] = datetime.now().isoformat()
    save_json(CANON_FILE, canon)
    save_json(TRANSCRIPTS_FILE, transcripts[-500:])
    synthesize_beliefs(transcripts, mind)

    print(f"\n✅ Training complete!")
    print(f"   Dialogues completed: {completed}")
    print(f"   Dialogues failed: {failed}")
    print(f"   Canon entries added: {canon_added}")
    print(f"   Final canon size: {len(canon_entries)}")

if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    train(n)