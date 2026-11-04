"""OpenRouter error handling, using a fake transport (no network, no cost)."""

import asyncio
import json

import httpx
import pytest

from app import llm
from app.errors import ModelAccountProblem, ModelUnavailable


@pytest.fixture(autouse=True)
def fake_settings(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "test/model")
    monkeypatch.setattr("app.config._load_env_file", lambda *a, **k: None)


def use_responses(monkeypatch, *responses):
    """Each request gets the next response; returns a list that records request count."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return responses[min(len(seen), len(responses)) - 1]

    monkeypatch.setattr(llm, "_transport", httpx.MockTransport(handler))
    return seen


def ok(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def run():
    return asyncio.run(llm.call("system", "user"))


def test_returns_parsed_json(monkeypatch):
    seen = use_responses(monkeypatch, ok(json.dumps({"mentions": []})))
    assert run() == {"mentions": []}
    assert len(seen) == 1


def test_strips_code_fence(monkeypatch):
    use_responses(monkeypatch, ok('```json\n{"a": 1}\n```'))
    assert run() == {"a": 1}


@pytest.mark.parametrize("status,body,code", [
    (401, {"error": {"message": "No auth credentials found"}}, "model_key_invalid"),
    (402, {"error": {"message": "Insufficient credits"}}, "model_out_of_credit"),
    (403, {"error": {"message": "Key limit exceeded"}}, "model_refused"),
    (400, {"error": {"message": "x/y is not a valid model ID"}}, "model_not_found"),
    (404, {"error": {"message": "No endpoints found for model x/y"}}, "model_not_found"),
])
def test_account_problems_fail_fast_with_reason(monkeypatch, status, body, code):
    seen = use_responses(monkeypatch, httpx.Response(status, json=body))
    with pytest.raises(ModelAccountProblem) as exc:
        run()
    assert exc.value.code == code
    assert len(seen) == 1  # no pointless retry


@pytest.mark.parametrize("status", [429, 500, 503])
def test_temporary_problems_retry_once_then_succeed(monkeypatch, status):
    seen = use_responses(monkeypatch, httpx.Response(status), ok('{"a": 1}'))
    assert run() == {"a": 1}
    assert len(seen) == 2


def test_temporary_problem_twice_is_unavailable(monkeypatch):
    seen = use_responses(monkeypatch, httpx.Response(503))
    with pytest.raises(ModelUnavailable):
        run()
    assert len(seen) == 2


def test_bad_json_retries_then_unavailable(monkeypatch):
    seen = use_responses(monkeypatch, ok("not json"))
    with pytest.raises(ModelUnavailable):
        run()
    assert len(seen) == 2


def test_other_400_is_unavailable_without_retry(monkeypatch):
    seen = use_responses(monkeypatch, httpx.Response(400, json={"error": {"message": "bad request"}}))
    with pytest.raises(ModelUnavailable):
        run()
    assert len(seen) == 1
