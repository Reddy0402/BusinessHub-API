"""Small OpenRouter client used by the AI Smart Task Assistant.

Configuration (Railway Variables in production, a local .env file in development):
  OPENROUTER_API_KEY  - required for the AI endpoints; never commit it
  OPENROUTER_MODEL    - optional; one model id, or a comma-separated list. OpenRouter
                        tries them in order, so a busy (rate-limited) free model falls
                        back to the next one. Defaults to DEFAULT_MODELS (all ":free", $0).

Tests never call the real API: they replace complete_json() with a fake.
"""

import json
import os
import re

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODELS = [
    "nvidia/nemotron-3.5-super-vl:free",
    "baidu/ernie-5.5-flash-preview:free",
    "google/gemma-4-31b-it:free",
]
TIMEOUT_SECONDS = 45


class AIError(Exception):
    """The AI feature could not produce an answer. `status_code` is the HTTP status to return."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def model_list() -> list[str]:
    configured = [m.strip() for m in os.getenv("OPENROUTER_MODEL", "").split(",") if m.strip()]
    return configured or DEFAULT_MODELS


def model_name() -> str:
    """The preferred model (logged with each AI call)."""
    return model_list()[0]


def _extract_json(text: str) -> dict:
    """Free models sometimes wrap JSON in prose or ``` fences; pull out the object."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise AIError("The AI returned an answer that could not be read. Please try again.", 502)
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        raise AIError("The AI returned an answer that could not be read. Please try again.", 502)
    if not isinstance(data, dict):
        raise AIError("The AI returned an answer that could not be read. Please try again.", 502)
    return data


def complete_json(system_prompt: str, user_prompt: str) -> dict:
    """Send one chat request to OpenRouter and return the JSON object in the reply."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise AIError("AI features are not configured: set OPENROUTER_API_KEY.", 503)

    try:
        response = httpx.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {api_key}", "X-Title": "TeamTask API"},
            json={
                "model": model_name(),
                "models": model_list(),  # OpenRouter fallback order
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.HTTPError:
        raise AIError("Could not reach the AI service. Please try again.", 503)

    if response.status_code == 429:
        raise AIError("The free AI model is busy (rate limit). Please try again in a minute.", 503)
    if response.status_code in (401, 403):
        raise AIError("The AI service rejected the API key. Check OPENROUTER_API_KEY.", 503)
    if response.status_code >= 400:
        raise AIError(f"The AI service returned an error (HTTP {response.status_code}).", 502)

    try:
        content = response.json()["choices"][0]["message"]["content"] or ""
    except (ValueError, KeyError, IndexError, TypeError):
        raise AIError("The AI returned an answer that could not be read. Please try again.", 502)
    return _extract_json(content)
