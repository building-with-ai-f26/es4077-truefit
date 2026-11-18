"""Request limits for the live site. The AI routes spend the owner's OpenRouter credit, so each visitor and the
whole site are capped; the other API routes make the server do work (fetch a page, read a file, build a download),
so each visitor gets a looser limit. Counts are kept in memory: one server, and they reset when it restarts.
"""

import time
from collections import defaultdict, deque

AI_ROUTES = {"/api/start-date", "/api/tailor", "/api/verify-bullet"}
OTHER_ROUTES = {"/api/read-docx", "/api/posting-link", "/api/resume-docx", "/api/resume-pdf"}
MINUTE, DAY = 60, 24 * 3600
AI_PER_MINUTE, AI_PER_DAY, SITE_AI_PER_DAY = 10, 50, 200  # the site-wide cap is the owner's choice (Nov 18)
OTHER_PER_MINUTE = 30

MESSAGES = {
    "rate_limited": "Too many requests. Try again in a minute.",
    "daily_limit": "You've reached today's limit. Try again tomorrow.",
    "site_daily_limit": "TrueFit has reached its limit for today. Try again tomorrow.",
}

_now = time.monotonic  # tests swap in a fake clock
_visitors: dict[tuple[str, str], deque] = defaultdict(deque)
_site_ai: deque = deque()


def reset() -> None:
    _visitors.clear()
    _site_ai.clear()


def visitor(cloudflare: str | None, forwarded_for: str | None, direct: str | None) -> str:
    """The visitor's address. On Render, Cloudflare sets CF-Connecting-IP to the real visitor (visitors can't fake
    it); the last X-Forwarded-For entry there is one of several relay servers. Elsewhere, that last entry is the
    one the host adds; earlier ones can be faked."""
    if cloudflare:
        return cloudflare.strip()
    if forwarded_for:
        return forwarded_for.split(",")[-1].strip()
    return direct or "unknown"


def check(path: str, who: str) -> str | None:
    """Count this request and return a refusal code, or None if it may go ahead. Refused requests aren't counted."""
    now = _now()
    if path in AI_ROUTES:
        times = _visitors[(who, "ai")]
        _drop_older(times, now - DAY)
        _drop_older(_site_ai, now - DAY)
        if sum(1 for t in times if t > now - MINUTE) >= AI_PER_MINUTE:
            return "rate_limited"
        if len(times) >= AI_PER_DAY:
            return "daily_limit"
        if len(_site_ai) >= SITE_AI_PER_DAY:
            return "site_daily_limit"
        times.append(now)
        _site_ai.append(now)
    elif path in OTHER_ROUTES:
        times = _visitors[(who, "other")]
        _drop_older(times, now - MINUTE)
        if len(times) >= OTHER_PER_MINUTE:
            return "rate_limited"
        times.append(now)
    return None


def _drop_older(times: deque, cutoff: float) -> None:
    while times and times[0] <= cutoff:
        times.popleft()
