"""The one place TrueFit calls the AI model (via OpenRouter).

Prompts and responses are never logged: they contain resume and posting text.
"""

import json

import httpx

from app.config import get_settings
from app.errors import ModelUnavailable

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT_SECONDS = 60
ATTEMPTS = 2  # first try + one retry


async def call(system: str, user: str) -> dict:
    """Send one system + user message and return the model's reply parsed as a JSON object."""
    settings = get_settings()
    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    headers = {"Authorization": f"Bearer {settings.api_key}"}

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        for _ in range(ATTEMPTS):
            try:
                response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                parsed = json.loads(_strip_code_fence(content))
                if isinstance(parsed, dict):
                    return parsed
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
                continue
    raise ModelUnavailable()


def _strip_code_fence(text: str) -> str:
    """Some models wrap JSON in ```json fences even in JSON mode."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text
