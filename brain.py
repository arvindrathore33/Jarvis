"""
JARVIS Smart Brain — API Fallback Chain
Gemini (free) → Groq (free 70B) → Local Ollama
Automatically switches when quota exceeded or API fails
"""

import ollama
import os
import requests

CLAUDE_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_KEY  = os.getenv("GEMINI_API_KEY", "")
GROQ_KEY    = os.getenv("GROQ_API_KEY", "")
LOCAL_MODEL = os.getenv("JARVIS_MODEL", "qwen2.5:1.5b")

# ── Rate-limit counter ────────────────────────────────────────────────────────
# Tracks requests per provider. Free tier limits:
#   Groq:   14,400 req/day
#   Gemini: 1,500 req/day (free tier)
_request_counts = {"claude": 0, "gemini": 0, "groq": 0, "local": 0}
_FREE_LIMITS = {"groq": 14400, "gemini": 1500}

def _track(provider: str):
    """Increment counter and warn when approaching free tier limit."""
    _request_counts[provider] = _request_counts.get(provider, 0) + 1
    count = _request_counts[provider]
    limit = _FREE_LIMITS.get(provider)
    if limit:
        pct = count / limit * 100
        if pct >= 90:
            print(f"\033[1;31m[BRAIN] ⚠️  {provider.upper()} at {pct:.0f}% of daily limit ({count}/{limit})\033[0m")
        elif pct >= 75:
            print(f"\033[1;33m[BRAIN] {provider.upper()} at {pct:.0f}% of daily limit ({count}/{limit})\033[0m")

def get_request_counts():
    """Return current request counts for all providers."""
    return dict(_request_counts)


def ask_claude(messages, system):
    """Claude API — best quality, costs tokens"""
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": CLAUDE_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "system": system,
            "messages": messages
        },
        timeout=30
    )
    data = r.json()
    if "error" in data:
        err = data["error"].get("type", "")
        if err in ("insufficient_quota", "overloaded_error"):
            raise Exception("CLAUDE_QUOTA_EXCEEDED")
        raise Exception(f"Claude error: {data['error']}")
    _track("claude")
    return data["content"][0]["text"]


def ask_gemini(messages, system):
    """Gemini API — free tier (1,500 req/day), strong reasoning"""
    # Convert messages to Gemini format
    contents = [{"role": "user" if m["role"] == "user" else "model",
                 "parts": [{"text": m["content"]}]} for m in messages]
    # Prepend system prompt as first user turn
    contents = [{"role": "user", "parts": [{"text": system}]},
                {"role": "model", "parts": [{"text": "Understood. I am JARVIS."}]}] + contents
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}",
        json={"contents": contents, "generationConfig": {"maxOutputTokens": 2000}},
        timeout=30
    )
    data = r.json()
    if "error" in data:
        raise Exception(f"Gemini error: {data['error'].get('message', data['error'])}")
    _track("gemini")
    return data["candidates"][0]["content"]["parts"][0]["text"]


def ask_groq(messages, system):
    """Groq API — free tier, Llama3 70B, very fast"""
    from groq import Groq
    client = Groq(api_key=GROQ_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=2000,
        temperature=0.7
    )
    _track("groq")
    return response.choices[0].message.content


def ask_local(messages, system):
    """Local Ollama — always works, fully offline, private"""
    response = ollama.chat(
        model=LOCAL_MODEL,
        messages=[{"role": "system", "content": system}] + messages
    )
    _track("local")
    # Support both dict-style (old) and attribute-style (new ollama library)
    try:
        return response.message.content
    except AttributeError:
        return response["message"]["content"]


def jarvis_brain(messages, system):
    """
    Smart fallback chain:
    1. Gemini API  — free 1,500 req/day (PRIMARY)
    2. Groq        — free 14,400 req/day, Llama3 70B
    3. Local Ollama — always works, 100% offline, private

    Claude is optional — only used if ANTHROPIC_API_KEY is set.
    """

    # ── Optional: Claude API (if you ever get a key) ────────
    if CLAUDE_KEY and CLAUDE_KEY.strip() and not CLAUDE_KEY.strip().startswith("#"):
        try:
            print("[BRAIN] Claude API", end=" ")
            reply = ask_claude(messages, system)
            return reply, "claude"
        except Exception as e:
            print(f"→ error ({e}), trying Gemini...")

    # ── Tier 1: Gemini (PRIMARY free API) ─────────────
    if GEMINI_KEY and GEMINI_KEY.strip() and not GEMINI_KEY.strip().startswith("#"):
        try:
            print("[BRAIN] Gemini API", end=" ")
            reply = ask_gemini(messages, system)
            return reply, "gemini"
        except Exception as e:
            print(f"→ error ({e}), trying Groq...")

    # ── Tier 2: Groq free 70B ─────────────────────────
    if GROQ_KEY and GROQ_KEY.strip() and not GROQ_KEY.strip().startswith("#"):
        try:
            print("[BRAIN] Groq 70B", end=" ")
            reply = ask_groq(messages, system)
            return reply, "groq"
        except Exception as e:
            print(f"→ error ({e}), switching to local...")

    # ── Tier 3: Local Ollama (always available) ───────
    print("[BRAIN] Local Ollama", end=" ")
    reply = ask_local(messages, system)
    return reply, "local"
