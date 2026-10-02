"""
Deterministic news & sentiment analysis (spec sections 5, 9, 26 item #9).

This package turns sourced headlines into an auditable, deterministic sentiment
read. It is deterministic-first by design: the baseline classifier is a
transparent finance lexicon (:mod:`.sentiment`), never an LLM, so the same
headline always yields the same score and every score is explainable by the
terms it matched. An LLM-backed classifier is a clean future extension behind
the same ``classify`` contract -- the spec permits LLMs for language
understanding provided the source data stays traceable (section 5).
"""

from __future__ import annotations

from .sentiment import LexiconSentiment, classify

__all__ = ["LexiconSentiment", "classify"]
