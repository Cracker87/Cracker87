"""Redaction: strip secrets from captured text BEFORE it is persisted."""

from __future__ import annotations

import re

REDACTED = "[REDACTED]"

# Order matters: more specific patterns first.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("private_key_block", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL)),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b")),
    ("generic_secret_assign", re.compile(
        r"(?i)\b(api[_-]?key|secret|token|passwd|password|pwd)"
        r"(\s*[:=]\s*)(\"[^\"\s]{6,}\"|'[^'\s]{6,}'|[^\s\"']{6,})")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{16,}=*")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
]

_CARD_CANDIDATE = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _redact_cards(text: str) -> str:
    def repl(m: re.Match) -> str:
        digits = re.sub(r"[ -]", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            return REDACTED
        return m.group(0)
    return _CARD_CANDIDATE.sub(repl, text)


def redact(text: str) -> str:
    """Return text with recognized secrets replaced by [REDACTED]."""
    for name, pat in _PATTERNS:
        if name == "generic_secret_assign":
            text = pat.sub(lambda m: m.group(1) + m.group(2) + REDACTED, text)
        else:
            text = pat.sub(REDACTED, text)
    return _redact_cards(text)
