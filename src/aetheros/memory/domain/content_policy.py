"""
Content-safety policy for memory payloads (spec Phase 3).

Two small, deterministic concerns that must exist from the *first* write path,
not deferred to a later security phase (contract: "Security foundations must
exist from the first write path"):

* **Safe content limits** -- a memory is a single statement, not a document
  store. :data:`MAX_CONTENT_CHARS` bounds the searchable ``content`` and
  :data:`MAX_PAYLOAD_BYTES` bounds the serialised structured payload so an
  unbounded blob can never silently land in SQLite, the vector pool or an event.

* **Secret redaction / rejection** -- obvious credentials (API keys, bearer
  tokens, private-key blocks, ``password=``/``api_key=`` assignments) must not
  be mixed into persisted text. This is a conservative *foundation*, deliberately
  not an exhaustive DLP scanner: it favours no false-positives on ordinary
  trading prose and is the hook the later security phase extends. It never
  claims to catch every secret -- see :class:`ContentPolicy`.

The mechanism lives here as pure, side-effect-free functions so the domain owns
it and every writer, exporter and cache can reuse the same rules. The write-path
*enforcement* (which policy is applied) is wired in the validator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# A memory's human-readable statement. Generous, but bounded: longer text is a
# document and belongs to ingestion (Phase 17, deferred), not a single memory.
MAX_CONTENT_CHARS = 20_000

# Upper bound on the JSON-serialised structured payload (``data``) in bytes.
MAX_PAYLOAD_BYTES = 262_144  # 256 KiB

# Replacement token left in place of a redacted secret, tagged with its kind so
# the audit trail shows *that* something was removed without revealing it.
REDACTION_TOKEN = "[REDACTED:{kind}]"


class SecretAction(str, Enum):
    """What to do when content appears to contain a secret (spec Phase 3)."""

    REDACT = "redact"  # replace the secret span, keep the memory (default)
    REJECT = "reject"  # refuse the write entirely
    ALLOW = "allow"  # keep as-is (only for trusted, already-sanitised input)


# Conservative, high-precision patterns. Each is (kind, compiled regex). Order
# matters only for the kind label; spans are redacted independently.
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private_key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"
            r".*?-----END (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("gcp_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{36,}\b")),
    ("bearer_token", re.compile(r"\bBearer\s+[0-9A-Za-z._\-]{20,}\b")),
    (
        "assigned_secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|password|passwd|access[_-]?token|"
            r"auth[_-]?token|client[_-]?secret)\b\s*[:=]\s*"
            r"['\"]?([^\s'\"]{6,})['\"]?"
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class ContentPolicy:
    """
    How the write path treats memory content (spec Phase 3).

    Immutable value object so a policy is safe to share. ``on_secret`` chooses
    redaction (default), rejection or allow; the limits bound size. This is a
    *foundation*, not a guarantee that all secrets are detected.
    """

    max_content_chars: int = MAX_CONTENT_CHARS
    max_payload_bytes: int = MAX_PAYLOAD_BYTES
    on_secret: SecretAction = SecretAction.REDACT


def scan_secrets(text: str) -> list[str]:
    """
    Return the distinct kinds of secret found in ``text`` (possibly empty).

    Deterministic and read-only -- used both to decide rejection and to label a
    redaction. Non-string / empty input yields no findings.
    """
    if not text:
        return []
    kinds: list[str] = []
    for kind, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            if kind not in kinds:
                kinds.append(kind)
    return kinds


def redact_text(text: str) -> tuple[str, list[str]]:
    """
    Replace secret spans in ``text`` with a kind-tagged token.

    Returns the cleaned text and the distinct kinds redacted. For the
    ``assigned_secret`` pattern only the value (group 1) is replaced so the key
    name stays legible (e.g. ``api_key=[REDACTED:assigned_secret]``).
    """
    if not text:
        return text, []
    redacted: list[str] = []
    out = text
    for kind, pattern in _SECRET_PATTERNS:
        token = REDACTION_TOKEN.format(kind=kind)

        def _sub(match: re.Match[str], _kind: str = kind, _token: str = token) -> str:
            nonlocal redacted
            if _kind not in redacted:
                redacted.append(_kind)
            if match.groups():
                # Replace only the captured secret value, keep surrounding text.
                start, end = match.span(1)
                return match.group(0)[: start - match.start()] + _token
            return _token

        out = pattern.sub(_sub, out)
    return out, redacted
