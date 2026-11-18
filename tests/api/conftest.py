from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import gaps, llm, rate_limit, start_date
from app.errors import ModelUnavailable
from app.main import app

TODAY = date(2026, 11, 4)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    rate_limit.reset()  # each test starts with no requests counted


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(start_date, "today_ny", lambda: TODAY)


class FakeLLM:
    """Replaces llm.call: returns queued replies in order and records every call.

    The gap-list call runs alongside tailoring, so it gets its own reply (gaps_reply) and its own record
    (gap_calls) instead of taking a turn in the queue.
    """

    def __init__(self):
        self.replies = []
        self.calls = []
        self.gaps_reply = {"requirements": []}
        self.gap_calls = []

    def queue(self, *replies):
        self.replies.extend(replies)

    async def __call__(self, system: str, user: str) -> dict:
        if system == gaps.GAPS_PROMPT:
            self.gap_calls.append({"system": system, "user": user})
            return self.gaps_reply
        self.calls.append({"system": system, "user": user})
        reply = self.replies.pop(0)
        if reply is ModelUnavailable or isinstance(reply, ModelUnavailable):
            raise ModelUnavailable()
        return reply


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(llm, "call", fake)
    return fake
