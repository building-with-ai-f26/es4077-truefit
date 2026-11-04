"""The one place TrueFit calls the AI model (via OpenRouter).

Prompts and responses are never logged: they contain resume and posting text.
"""

import json

import httpx

from app.config import get_settings
from app.errors import ModelAccountProblem, ModelUnavailable

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT_SECONDS = 60
ATTEMPTS = 2  # first try + one retry, only for problems that might be temporary

_transport: httpx.AsyncBaseTransport | None = None  # tests swap in a fake transport


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

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, transport=_transport) as client:
        for _ in range(ATTEMPTS):
            try:
                response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            except httpx.HTTPError:
                continue
            _raise_if_account_problem(response)
            if response.status_code != 200:
                continue  # 429 rate limit, 5xx outage: worth one retry
            try:
                content = response.json()["choices"][0]["message"]["content"]
                parsed = json.loads(_strip_code_fence(content))
            except (KeyError, IndexError, TypeError, ValueError):
                continue
            if isinstance(parsed, dict):
                return parsed
    raise ModelUnavailable()


def _raise_if_account_problem(response: httpx.Response) -> None:
    """Fail fast with a clear reason when retrying can't help."""
    status = response.status_code
    if status == 401:
        raise ModelAccountProblem(
            "model_key_invalid",
            "The OpenRouter key in .env isn't valid. Check OPENROUTER_API_KEY (it starts with sk-or-v1-) and restart TrueFit.")
    if status == 402:
        raise ModelAccountProblem(
            "model_out_of_credit",
            "TrueFit's AI account is out of credit. Add credits at openrouter.ai/settings/credits, then try again.")
    if status == 403:
        raise ModelAccountProblem(
            "model_refused",
            "OpenRouter refused the request; the key may have hit its credit limit. Check the key's limit at openrouter.ai.")
    if status in (400, 404) and "model" in _error_message(response).lower():
        raise ModelAccountProblem(
            "model_not_found",
            "The model in .env (OPENROUTER_MODEL) wasn't found on OpenRouter. Copy its exact name from openrouter.ai/models.")
    if status == 400:
        raise ModelUnavailable()  # a malformed request won't succeed on retry


def _error_message(response: httpx.Response) -> str:
    try:
        return str(response.json().get("error", {}).get("message", ""))
    except ValueError:
        return response.text


def _strip_code_fence(text: str) -> str:
    """Some models wrap JSON in ```json fences even in JSON mode."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text
