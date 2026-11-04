"""Checks that a quote the model returned really appears in the source text (Constitution II)."""

import re

_WHITESPACE = re.compile(r"\s+")


def _collapse(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def quote_in(source: str, quote: str) -> bool:
    """True only if quote is a non-empty exact substring of source, ignoring whitespace differences."""
    quote = _collapse(quote or "")
    return bool(quote) and quote in _collapse(source)
