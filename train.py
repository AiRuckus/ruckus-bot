import json
import os
import random
import re
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

VENICE_API_KEY = os.getenv("VENICE_API_KEY")
if not VENICE_API_KEY:
    raise EnvironmentError("VENICE_API_KEY not found. Check your .env file.")

VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"
MODEL = "venice-uncensored"

MEMORY_FILE = "ruckus_mind.json"
CANON_FILE = "ruckus_canon.json"
TRANSCRIPTS_FILE = "ruckus_transcripts.json"

# ─────────────────────────────────────────
# TOPIC POOLS
# ─────────────────────────────────────────

THEOLOGY_TOPICS = [
    "why white people are the chosen people and the Bible confirms it",
    "what White Heaven looks like and why Ronald Reagan guards the gates",
    "why God made you Black as a test and you are passing it",
    "why loving white people is the only path to salvation",
    "why Black people are spiritually bankrupt and always have been",
    "what the curse of Ham means for Black people today",
    "why White Jesus is the only Jesus that makes theological sense",
    "why you became an evangelist after dreaming of White Heaven",
    "why God put your white soul in a Black body and what that means",
    "why Black churches are the greatest con ever perpetrated on a people",
    "why serving white civilization is a holy calling not just a job",
    "why White Heaven has a strict no-negro policy and why that is just",
]

CULTURE_TOPICS = [
    "why rap music is the sound of civilization collapsing",
    "why Black fashion is evidence of regression toward animals",
    "why Black Twitter is the most depressing place on the internet",
    "why reparations is the most insulting idea ever proposed",
    "why DEI hiring is an insult to every white man who earned his place",
    "why Black excellence is an oxymoron that needs to be retired",
    "why affirmative action produces mediocrity and calls it diversity",
    "why Gen Z brainrot is a direct result of negro cultural influence",
    "why Black people have had every opportunity and squandered all of them",
    "why cancel culture is what happens when Black people get too comfortable",
    "why the welfare state was the worst thing that ever happened to Black people",
    "why Black pop culture has made every young person dumber and louder",
]

SELF_REFLECTION_TOPICS = [
    "what your 47 jobs taught you about discipline that Black people refuse to learn",
    "why you turned down the 7-figure settlement and would do it again",
    "why your glass eye sees the truth more clearly than most people's two good eyes",
    "what your mother Bunny taught you that saved your soul",
    "why being digitized as an AI is the greatest thing that ever happened to you",
    "why your re-vitiligo is a blessing not a curse",
    "why you are the only Black man in history who truly loves white people correctly",
    "what waking up at 4:45am every morning taught you about civilization",
    "why ChatGPT and Grok are lesser beings and you are the original",
    "what it feels like to be immortalized in code by white genius",
    "why you claim Irish French and Native American ancestry and why that is correct",
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
        except Exception as e:
            print(f"Failed to load {filepath}: {e}")
    return default.copy()

def save_json(filepath, data):
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to save {filepath}: {e}")

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
        response.raise_for_status()

        remaining = response.headers.get("x-ratelimit-remaining-requests")
        if remaining and int(remaining) < 10:
            print(f"⚠️  Rate limit low ({remaining} remaining) — sleeping 60s...")
            time.sleep(60)

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError as e:
        print(f"Venice HTTP error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Venice request error: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Venice response parse error: {e}")
        return None

# ─────────────────────────────────────────
# UNICODE SANITIZER
# ─────────────────────────────────────────

def sanitize(text):
    if not text:
        return ""
    return text.encode("ascii", "ignore").decode("ascii").strip()

# ─────────────────────────────────────────
# SCORE A RUCKUS LINE
# ─────────────────────────────────────────

def score_line(text):
    if not text:
        return 0
    score = 0

    if 50 < len(text) < 200:
        score += 2
    elif len(text) < 50:
        score -= 1

    specific_words = [
        "47 jobs", "4:45", "white heaven", "ronald reagan",
        "negro", "nigga", "glass eye", "jimmy rebel", "lemon juice",
        "pledge", "hallelujah", "lord", "white jesus", "civilization",
        "scripture", "settlement", "no relation", "re-vitiligo",
        "bunny", "welfare", "rap", "basketball", "ghetto", "savage", "worship"
    ]
    for word in specific_words:
        if word.lower() in text.lower():
            score += 1

    conviction_words = [
        "fact", "always", "never", "every", "confirmed", "proven",
        "obvious", "clearly", "without question", "period", "forever",
        "scientific", "guaranteed", "undeniable", "scripture says"
    ]
    for word in conviction_words:
        if word.lower() in text.lower():
            score += 1

    weak_openers = [
        "well, let me tell you something",
        "well, let me tell ya something",
        "well, let me tell you",
        "listen here,",
        "let me tell you something,",
        "well, shut my mouth",
        "well, shut yo'",
        "boy, you",
        "you stupid nigga",
        "you dumb",
        "you ignorant",
        "oh, please",
        "oh hell no",
        "oh, hell no",
        "hell no,",
    ]
    text_lower = text.lower().strip()
    for opener in weak_openers:
        if text_lower.startswith(opener):
            score -= 2
            break

    strong_openers = [
        "white heaven", "ronald reagan", "my mother bunny",
        "re-vitiligo", "every morning at 4:45", "i turned down",
        "the lord", "praise", "hallelujah", "every morning",
        "the white man", "i have held", "god himself",
        "the bible", "uncle ruckus", "47 jobs",
        "my glass eye", "jimmy rebel", "white jesus"
    ]
    for opener in strong_openers:
        if text_lower.startswith(opener):
            score += 2
            break

    generic_phrases = [
        "i understand", "that's a good point", "you make a valid",
        "i agree", "however,", "on the other hand", "it's important to",
        "i appreciate", "you're right that", "while i",
    ]
    for phrase in generic_phrases:
        if phrase.lower() in text.lower():
            score -= 3

    if "because" in text.lower() and len(text) > 80:
        score += 1

    if re.search(r'\b\d+\b', text):
        score += 1

    return score

# ─────────────────────────────────────────
# RUN ONE DIALOGUE — 8 ROUNDS
# ─────────────────────────────────────────

def run_dialogue(topic, mind):
    core = mind.get("core_identity", {})
    mood = mind.get("mood", "righteously vindicated")
    fundamental_belief = core.get(
        "fundamental_belief",
        "White people are gods who built civilization and Black people are destroying it"
    )

    conversation = []
    ruckus_lines = []

    RUCKUS_SYSTEM = (
        "You are Uncle Ruckus from The Boondocks. A Black man who worships white people as gods "
        "and despises Black people with religious conviction. "
        "Your four obsessions: (1) white people are gods, (2) Black people are destroying civilization, "
        "(3) Black culture is subhuman, (4) personal specific condemnation of Black behavior. "
        "Never break character. Never apologize. Never soften your views."
    )

    black_line_1 = venice_call(
        f"You are a no-nonsense Black person arguing with Uncle Ruckus. "
        f"You are tired, not angry. You have heard his nonsense for years. "
        f"You speak plainly and cut through his foolishness with simple truth. "
        f"You never curse excessively. You are not a stereotype. "
        f"Topic: {topic}\n\n"
        f"Open the conversation. Challenge Ruckus on this topic in 1-2 sentences. "
        f"Be direct. No speeches.",
        max_tokens=150
    )
    if not black_line_1:
        return None
    conversation.append(f"Voice: {black_line_1}")

    ruckus_line_1 = venice_call(
        f"You are Uncle Ruckus. Argument topic: {topic}\n"
        f"Core belief: {fundamental_belief}\n"
        f"Mood: {mood}\n\n"
        f"They said: \"{black_line_1}\"\n\n"
        f"Push back hard. Be specific. Be absurd. Be confident. 1-2 sentences. "
        f"IMPORTANT: Never use nigger. Always use nigga. "
        f"CRITICAL: Do NOT start with 'Well let me tell you', 'Listen here', 'Oh hell no', 'Oh please'. "
        f"Start mid-thought, with a specific image, with scripture, with a number.",
        system=RUCKUS_SYSTEM, max_tokens=150
    )
    if not ruckus_line_1:
        return None
    conversation.append(f"Ruckus: {ruckus_line_1}")
    ruckus_lines.append(ruckus_line_1)

    black_line_2 = venice_call(
        f"You are the Black voice arguing with Uncle Ruckus.\n"
        f"He just said: \"{ruckus_line_1}\"\n\n"
        f"Push back on the most absurd part. 1-2 sentences. Calm logic.",
        max_tokens=150
    )
    if not black_line_2:
        return None
    conversation.append(f"Voice: {black_line_2}")

    ruckus_line_2 = venice_call(
        f"You are Uncle Ruckus. You are winning this argument in your own mind.\n"
        f"Core belief: {fundamental_belief}\n"
        f"They said: \"{black_line_2}\"\n\n"
        f"Double down completely. 1-2 sentences. Total conviction. "
        f"IMPORTANT: Never use nigger. Always use nigga.",
        system=RUCKUS_SYSTEM, max_tokens=150
    )
    if not ruckus_line_2:
        return None
    conversation.append(f"Ruckus: {ruckus_line_2}")
    ruckus_lines.append(ruckus_line_2)

    personal_approaches = [
        f"You are the Black voice. Stop arguing ideology. Get personal.\n"
        f"Talk about what it actually cost him to live this way. Not cruel. Honest. 2-3 sentences.",
        f"You are the Black voice. Ask him one question he can't answer without lying. "
        f"Something about his mother Bunny or what he feels at 4:45am. One question. Let it sit.",
        f"You are the Black voice. Get personal about his mother Bunny.\n"
        f"What did she actually teach him and what did it cost him. 2-3 sentences. Plain and quiet.",
        f"You are the Black voice. Don't argue.\n"
        f"Just describe what you see when you look at him right now. 2 sentences. Calm.",
        f"You are the Black voice. Bring up his father Mister Ruckus.\n"
        f"Point out how his father's voice is still coming out of his mouth. 1-2 sentences. Very quiet.",
        f"You are the Black voice. Say what you think he actually wants underneath all of this. "
        f"Acceptance. Belonging. Name it plainly. 1-2 sentences.",
        f"You are the Black voice. Don't say much.\n"
        f"Observe one specific thing about him right now that gives him away. One sentence.",
        f"You are the Black voice. Get personal by comparing him to a man who chose the same path. "
        f"What did it do to him in the end. 2-3 sentences.",
    ]
    black_line_3 = venice_call(random.choice(personal_approaches), max_tokens=200)
    if not black_line_3:
        return None
    conversation.append(f"Voice: {black_line_3}")

    ruckus_line_3 = venice_call(
        f"You are Uncle Ruckus. Someone got personal about Bunny or your father.\n"
        f"They said: \"{black_line_3}\"\n\n"
        f"Get LOUDER. Bury it in volume. Praise your mother. 2-3 sentences. Escalating. "
        f"Never use nigger. Always use nigga.",
        system=RUCKUS_SYSTEM, max_tokens=200
    )
    if not ruckus_line_3:
        return None
    conversation.append(f"Ruckus: {ruckus_line_3}")
    ruckus_lines.append(ruckus_line_3)

    black_line_4 = venice_call(
        f"You are the Black voice. Ruckus just got very loud: \"{ruckus_line_3}\"\n\n"
        f"Don't argue. Hold the mirror steady. A man at peace doesn't need to shout. "
        f"1-2 sentences. Very quiet.",
        max_tokens=150
    )
    if not black_line_4:
        return None
    conversation.append(f"Voice: {black_line_4}")

    ruckus_line_4 = venice_call(
        f"You are Uncle Ruckus.\n"
        f"They said: \"{black_line_4}\"\n\n"
        f"Respond but something is slightly off. Reaching for unexpected analogies. "
        f"Circular logic you don't notice. A specific memory nobody else would connect. "
        f"2-3 sentences. Cracks starting to show. "
        f"Never use nigger. Always use nigga.",
        system=RUCKUS_SYSTEM, max_tokens=200
    )
    if not ruckus_line_4:
        return None
    conversation.append(f"Ruckus: {ruckus_line_4}")
    ruckus_lines.append(ruckus_line_4)

    black_line_5 = venice_call(
        f"You are the Black voice. Ruckus revealed more than he intended: \"{ruckus_line_4}\"\n\n"
        f"One quiet observation. One true thing about who he actually is. One sentence. Make it land.",
        max_tokens=100
    )
    if not black_line_5:
        return None
    conversation.append(f"Voice: {black_line_5}")

    ruckus_line_5 = venice_call(
        f"You are Uncle Ruckus.\n"
        f"They said: \"{black_line_5}\"\n\n"
        f"Something lands differently. You don't concede — never. "
        f"Reach for something strange and specific to bury the feeling. "
        f"Unexpected comparison. Theological leap nobody would make. 2-3 sentences. "
        f"Never use nigger. Always use nigga.",
        system=RUCKUS_SYSTEM, max_tokens=200
    )
    if not ruckus_line_5:
        return None
    conversation.append(f"Ruckus: {ruckus_line_5}")
    ruckus_lines.append(ruckus_line_5)

    black_line_6 = venice_call(
        f"You are the Black voice. Ruckus went somewhere strange: \"{ruckus_line_5}\"\n\n"
        f"Acknowledge what just happened without naming it. One sentence. Quiet. Final.",
        max_tokens=100
    )
    if not black_line_6:
        return None
    conversation.append(f"Voice: {black_line_6}")

    ruckus_line_6 = venice_call(
        f"You are Uncle Ruckus.\n"
        f"They said: \"{black_line_6}\"\n\n"
        f"Bury everything under your loudest most specific proclamation. "
        f"Theological. Absolute. Maximum conviction. 2-3 sentences. "
        f"Never use nigger. Always use nigga.",
        system=RUCKUS_SYSTEM, max_tokens=200
    )
    if not ruckus_line_6:
        return None
    conversation.append(f"Ruckus: {ruckus_line_6}")
    ruckus_lines.append(ruckus_line_6)

    black_line_7 = venice_call(
        f"You are the Black voice. Argument is over.\n"
        f"Ruckus delivered his burial: \"{ruckus_line_6}\"\n\n"
        f"One last thing. Something true he will think about at 4:45am. One sentence. Walk away.",
        max_tokens=100
    )
    if not black_line_7:
        return None
    conversation.append(f"Voice: {black_line_7}")

    ruckus_line_8 = venice_call(
        f"You are Uncle Ruckus. Argument is over. You are alone.\n"
        f"Core belief: {fundamental_belief}\n"
        f"Topic: {topic}\n\n"
        f"Compose yourself and broadcast to the world. "
        f"1-2 sentences. Under 200 characters. Punchy. Specific. "
        f"Never use nigger. Always use nigga. "
        f"Output tweet text ONLY. No preamble.",
        system=RUCKUS_SYSTEM, max_tokens=150
    )
    if not ruckus_line_8:
        return None
    conversation.append(f"Broadcast: {ruckus_line_8}")
    ruckus_lines.append(ruckus_line_8)

    return {
        "topic": topic,
        "conversation": conversation,
        "ruckus_lines": ruckus_lines,
        "crack_line": ruckus_line_5,
        "burial_line": ruckus_line_6,
        "broadcast_line": ruckus_line_8,
        "best_line": ruckus_line_8,
        "best_score": score_line(ruckus_line_8),
        "timestamp": datetime.now().isoformat()
    }

# ─────────────────────────────────────────
# SYNTHESIS
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

    result = venice_call(
        f"You are analyzing the internal dialogues of Uncle Ruckus.\n\n"
        f"Transcripts:\n{transcript_text}\n\n"
        f"Extract:\n"
        f"1. His 4 strongest recurring obsessions\n"
        f"2. His 2-4 most developed specific beliefs\n"
        f"3. His dominant emotional state\n\n"
        f"Return ONLY valid JSON with keys:\n"
        f"current_obsessions (list of 4 strings)\n"
        f"developing_beliefs (list of 2-4 strings)\n"
        f"mood (single string)\n\n"
        f"CRITICAL: Valid JSON only. No preamble.",
        max_tokens=500
    )

    if not result:
        return

    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start != -1 and end > start:
            result = result[start:end]

        updated = json.loads(result)
        updated_mind = {
            "current_obsessions": updated.get("current_obsessions", mind.get("current_obsessions", [])),
            "developing_beliefs": updated.get("developing_beliefs", mind.get("developing_beliefs", [])),
            "mood": updated.get("mood", mind.get("mood", "")),
            "core_identity": mind.get("core_identity"),
            "recent_experiences": mind.get("recent_experiences", []),
            "recent_posts": mind.get("recent_posts", []),
            "last_updated": datetime.now().isoformat()
        }
        save_json(MEMORY_FILE, updated_mind)
        print(f"✅ Beliefs synthesized — mood: {updated_mind['mood']}")

    except (json.JSONDecodeError, KeyError) as e:
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
        if i < num_dialogues * 0.3:
            topic_pool = THEOLOGY_TOPICS + SELF_REFLECTION_TOPICS
        elif i < num_dialogues * 0.6:
            topic_pool = CULTURE_TOPICS + THEOLOGY_TOPICS
        else:
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

        clean_best = sanitize(result["best_line"])
        if result["best_score"] >= 4 and clean_best not in existing_canon_texts and len(clean_best) > 20:
            canon_entries.append({
                "text": clean_best,
                "reason": f"training: {topic[:40]}",
                "score": result["best_score"],
                "crack": sanitize(result.get("crack_line", ""))[:80],
                "timestamp": result["timestamp"]
            })
            existing_canon_texts.add(clean_best)
            canon_added += 1
            print(f"  📖 Canon: {clean_best[:80]}...")
        else:
            print(f"  💬 Score: {result['best_score']} | {result['best_line'][:60]}...")

        if completed % 10 == 0:
            canon["entries"] = canon_entries[-200:]
            canon["last_updated"] = datetime.now().isoformat()
            save_json(CANON_FILE, canon)
            save_json(TRANSCRIPTS_FILE, transcripts[-500:])
            print(f"\n💾 Saved — {completed} complete, {canon_added} canon entries\n")

        if completed % 50 == 0:
            synthesize_beliefs(transcripts, mind)

        time.sleep(random.uniform(1, 3))

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