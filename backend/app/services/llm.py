"""
Central Claude API wrapper for TalentAI.
All LLM features (parsing, optimizer, auditor, debate, RAG) go through here.
Fault-tolerant: if no key or API failure, callers fall back to heuristics.
"""
import json
import re
from app.core.config import settings

client = None
llm_available = False

try:
    if settings.CLAUDE_API_KEY:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
        llm_available = True
        print("✅ Claude API client initialized")
    else:
        print("⚠️ No CLAUDE_API_KEY set — LLM features disabled, using heuristic fallbacks")
except Exception as e:
    print(f"⚠️ Claude client init failed: {e} — using heuristic fallbacks")


MODEL = "claude-haiku-4-5-20251001"   # fast + cheap, ideal for parsing/auditing


def ask_claude(prompt: str, system: str = "", max_tokens: int = 1500) -> str:
    """Send a prompt to Claude, return raw text response. Raises on failure."""
    if not llm_available:
        raise RuntimeError("Claude API not available")

    message = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system if system else "You are a helpful assistant.",
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def ask_claude_json(prompt: str, system: str = "", max_tokens: int = 1500) -> dict:
    """Send a prompt expecting a JSON response; parses and returns a dict.
    Strips markdown fences if the model wraps output in ```json blocks."""
    raw = ask_claude(prompt, system=system, max_tokens=max_tokens)

    # Strip ```json ... ``` fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)

    return json.loads(cleaned)