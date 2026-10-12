"""
Deterministic macro-release taxonomy.

This is intentionally a small, transparent, reproducible classifier -- NOT an
LLM, and not a data source. It answers exactly one question about a text it is
handed: *which* macro release does this title name? The spec's economic calendar
tracks six specific releases (CPI, FOMC, NFP, interest rates, GDP, employment
data), and without this vocabulary every one of them collapses into the single
opaque ``EventType.ECONOMIC`` with a free-text title -- so "tracks CPI / FOMC /
NFP" would be a claim about a string rather than a structural fact (spec
section 5, CLAUDE.md section 9).

Three properties are load-bearing:

* **It is a label, never a number.** The read carries no impact, no probability
  and no claim about price. The provider keeps owning impact, and nothing here
  overrides it -- filling in a canonical impact where a source said ``UNKNOWN``
  would be inventing sourced data.
* **Every call is auditable.** Like :mod:`..news.sentiment`, the read reports the
  terms it matched, so a classification can always be explained by the text that
  produced it.
* **``UNKNOWN`` is honest, not a failure.** A retail-sales print or a PMI is a
  macro release this taxonomy does not name, and saying so beats guessing at the
  nearest kind. Text with nothing to go on returns ``UNKNOWN`` with no terms.

Matching is deliberately conservative and word-boundary aware: the text is
lowercased and every non-alphanumeric run becomes a space, then a term matches
only as a whole word or phrase. So ``"NFP"`` matches and ``"gdpr"`` does not
match ``gdp``, and punctuation variants (``non-farm payrolls``) normalise onto
the same phrase as their spaced forms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..domain.event_calendar import MacroEventKind

# Ordered, and the order IS the precedence. Two pairs need it:
#
#   NFP before EMPLOYMENT -- non-farm payrolls *are* employment data, and their
#   titles ("Non-Farm Employment Change") contain the broader kind's words.
#   FOMC before INTEREST_RATE -- an FOMC decision is the specific case of a rate
#   decision, so "Fed Interest Rate Decision" must not fall through to the
#   generic kind.
#
# CPI sits above FOMC so inflation-specific language wins a title that mentions
# both (a "Fed's preferred inflation gauge" is an inflation release).
_LEXICON: tuple[tuple[MacroEventKind, tuple[str, ...]], ...] = (
    (
        MacroEventKind.NFP,
        (
            "nfp",
            "non farm payrolls",
            "nonfarm payrolls",
            "non farm payroll",
            "nonfarm payroll",
            "non farm employment",
            "payrolls",
        ),
    ),
    (
        MacroEventKind.CPI,
        (
            "cpi",
            "consumer price index",
            "producer price index",
            "ppi",
            "inflation",
        ),
    ),
    (
        MacroEventKind.FOMC,
        (
            "fomc",
            "federal open market committee",
            "federal reserve",
            "fed funds",
            "federal funds rate",
            "fed interest rate",
            "fed rate",
            "fed decision",
            "fed statement",
            "monetary policy decision",
        ),
    ),
    (
        MacroEventKind.INTEREST_RATE,
        (
            "interest rate",
            "interest rates",
            "rate decision",
            "rate hike",
            "rate cut",
            "policy rate",
            "repo rate",
            "basis points",
        ),
    ),
    (
        MacroEventKind.GDP,
        (
            "gdp",
            "gross domestic product",
        ),
    ),
    (
        MacroEventKind.EMPLOYMENT,
        (
            "unemployment",
            "jobless claims",
            "initial claims",
            "continuing claims",
            "jobs report",
            "employment",
            "labor market",
            "labour market",
        ),
    ),
)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True, slots=True)
class MacroRead:
    """The deterministic macro-release read for one piece of text."""

    kind: MacroEventKind
    matched_terms: tuple[str, ...]


def _normalise(text: str) -> str:
    """
    Lowercase ``text``, reduce every non-alphanumeric run to one space, and pad.

    The padding is what makes ``" term "`` a whole-word test: it lets a term
    match only at a real boundary, so ``gdp`` does not match inside ``gdpr``.
    """
    return f" {_NON_ALNUM_RE.sub(' ', text.lower()).strip()} "


def classify(text: str) -> MacroRead:
    """
    Classify ``text`` into the macro release it names, deterministically.

    Returns ``UNKNOWN`` with no matched terms when the text names no release
    this taxonomy knows -- an honest "not one of the six", never a guess.
    """
    haystack = _normalise(text)
    if haystack.strip() == "":
        return MacroRead(MacroEventKind.UNKNOWN, ())

    for kind, terms in _LEXICON:
        hits = tuple(term for term in terms if f" {term} " in haystack)
        if hits:
            return MacroRead(kind, hits)

    return MacroRead(MacroEventKind.UNKNOWN, ())
