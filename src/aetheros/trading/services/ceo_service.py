"""
Trading-CEO service -- the LLM narration layer over the deterministic core.

This is the first slice of the spec's Trading CEO (CLAUDE.md sections 4, 5, 10):
it runs the deterministic pipeline for an instrument and then has an
:class:`LLMProvider` narrate the resulting :class:`TradingReport` in plain
language. The division of labour is the spec's central rule -- the deterministic
core decides (direction, probability, risk, recommendation), the LLM only
*explains*; it is never the source of a number (sections 2, 3, 10, 28).

Three honesty guarantees are structural:

* **The report is authoritative.** The brief copies recommendation / direction /
  actionability straight off the deterministic report; the narration cannot
  change them. The full report dict is embedded in the brief as the source of
  truth, so any number in the prose is auditable against it.
* **The LLM is optional.** The core must work without an LLM (sections 1, 10): if
  no provider is wired, or the call fails, the brief falls back to a deterministic
  templated summary of the report rather than failing -- never a fabricated one.
* **The prompt forbids fabrication.** The system instruction tells the model to
  restate only what the report contains, to never invent prices/probabilities,
  and to preserve the "estimates, not guarantees" framing.

Richer multi-agent delegation (the CEO driving research/quant/critic sub-agents
via tool-calling) builds on this narration slice and remains a later increment.
"""

from __future__ import annotations

import json
import re

from ...config.settings import Settings
from ...core.interfaces.llm_provider import LLMProvider
from ...core.logging import get_logger
from ..domain.ceo_brief import CEOBrief
from ..domain.instrument import Instrument
from ..domain.report import TradingReport
from .orchestration_service import OrchestrationService

logger = get_logger("trading.ceo")

_TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1wk", "1w", "1mo"}

# Words that look like tickers but are plainly English in a free-text request;
# excluded by the deterministic (no-LLM) interpreter so "should I buy X" doesn't
# resolve "buy" as a symbol.
_STOPWORDS = frozenset(
    {
        "a", "an", "the", "is", "it", "of", "on", "in", "for", "to", "me", "my",
        "i", "we", "you", "should", "would", "could", "can", "do", "does", "did",
        "buy", "sell", "hold", "long", "short", "trade", "trading", "stock",
        "stocks", "share", "shares", "price", "prices", "analyze", "analyse",
        "analysis", "look", "check", "about", "whats", "what", "how", "why",
        "when", "now", "today", "this", "that", "week", "weekly", "day", "daily",
        "month", "monthly", "please", "give", "show", "tell", "report", "brief",
        "and", "or", "vs", "with", "at", "be", "get", "any", "good", "bad",
    }
)

_TF_WORDS = {
    "daily": "1d",
    "day": "1d",
    "weekly": "1wk",
    "week": "1wk",
    "monthly": "1mo",
    "month": "1mo",
    "hourly": "1h",
}

_TICKER_RE = re.compile(r"^[A-Za-z]{1,12}(:[A-Za-z]{1,8})?$")

_SYSTEM_PROMPT = (
    "You are the narration layer of a deterministic trading-analysis system. "
    "You are given a JSON trading report that was computed deterministically. "
    "Your ONLY job is to explain that report in clear, plain language. "
    "Hard rules you must never break:\n"
    "1. Never invent or alter any number -- every price, probability, score, "
    "level or percentage you mention must come verbatim from the JSON.\n"
    "2. Never upgrade the recommendation: if it is NO_TRADE or not actionable, "
    "say so plainly; do not imply a trade.\n"
    "3. Always preserve that probabilities are estimates, not guarantees, and "
    "that this is analysis, not advice.\n"
    "4. If the report is based on MOCK or unreliable data, state that the read "
    "is not reliable.\n"
    "Be concise: a short paragraph on the recommendation and the main evidence, "
    "then the key risks/limitations."
)


class TradingCEOService:
    """Deterministic-core-first CEO: compute the report, then narrate it."""

    def __init__(
        self,
        orchestration: OrchestrationService,
        settings: Settings,
        *,
        llm: LLMProvider | None = None,
    ) -> None:
        self._orchestration = orchestration
        self._settings = settings
        self._llm = llm

    async def brief(
        self,
        symbol: str | Instrument,
        timeframe: str | None = None,
        *,
        limit: int | None = None,
    ) -> CEOBrief:
        report = await self._orchestration.generate_report(
            symbol, timeframe, limit=limit
        )
        payload = report.to_dict()

        narrative, narrated_by = await self._narrate(report, payload)

        return CEOBrief(
            instrument_key=report.instrument.key,
            timeframe=report.analysis.timeframe_value,
            recommendation=report.recommendation.value,
            direction=report.direction.value,
            is_actionable=report.is_actionable,
            narrative=narrative,
            narrated_by=narrated_by,
            report=payload,
        )

    # ------------------------------------------------------------------

    async def _narrate(self, report: TradingReport, payload: dict) -> tuple[str, str]:
        """Narrate via the LLM when wired; otherwise a deterministic fallback.

        Any LLM failure degrades to the deterministic summary rather than sinking
        the brief -- the core must work without the LLM (spec sections 1, 10).
        """
        if self._llm is None:
            return self._fallback(report), "deterministic-fallback"
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Explain this trading report:\n\n"
                    + json.dumps(payload, default=str)
                ),
            },
        ]
        try:
            text = await self._llm.generate(messages)
        except Exception:
            logger.exception("LLM narration failed; using deterministic fallback")
            return self._fallback(report), "deterministic-fallback"
        if not isinstance(text, str) or not text.strip():
            return self._fallback(report), "deterministic-fallback"
        narrated_by = f"{self._llm.name}:{self._llm.model}"
        return text.strip(), narrated_by

    # ------------------------------------------------------------------

    async def respond(self, request: str) -> CEOBrief:
        """Interpret a free-text request, then brief the instrument it names.

        The LLM (when wired) extracts the instrument + timeframe from the plain
        request; a deterministic heuristic is the fallback so the CEO still works
        without an LLM. The deterministic report then does all the analysis -- the
        interpretation only chooses *what* to analyse, never *what the answer is*.
        Raises :class:`ValueError` when no instrument can be identified, so the
        caller can respond honestly rather than analysing a guess.
        """
        symbol, timeframe = await self._interpret(request)
        if symbol is None:
            raise ValueError(
                "Could not identify an instrument in the request. "
                "Name a symbol, e.g. 'brief AAPL' or 'AAPL:NASDAQ'."
            )
        return await self.brief(symbol, timeframe)

    async def _interpret(self, request: str) -> tuple[str | None, str]:
        """Resolve (symbol, timeframe) from free text: LLM-first, heuristic-fallback."""
        if self._llm is not None:
            parsed = await self._interpret_via_llm(request)
            if parsed is not None and parsed[0]:
                return parsed
        return self._interpret_heuristically(request)

    async def _interpret_via_llm(self, request: str) -> tuple[str | None, str] | None:
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract the financial instrument and timeframe the user wants "
                    "analysed. Reply with ONLY a JSON object "
                    '{"symbol": "<TICKER or TICKER:EXCHANGE or null>", '
                    '"timeframe": "<1d|1h|1wk|1mo|...>"}. Do not analyse or add '
                    "any other text. Use null for symbol if none is named."
                ),
            },
            {"role": "user", "content": request},
        ]
        try:
            raw = await self._llm.generate(messages)
            data = json.loads(self._extract_json(raw))
        except Exception:
            logger.exception("LLM request-interpretation failed; using heuristic")
            return None
        symbol = data.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip() or symbol.lower() == "null":
            return None
        timeframe = data.get("timeframe")
        if not isinstance(timeframe, str) or timeframe.strip().lower() not in _TIMEFRAMES:
            timeframe = "1d"
        return symbol.strip().upper(), timeframe.strip().lower()

    @staticmethod
    def _extract_json(text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            return text
        return text[start : end + 1]

    @staticmethod
    def _interpret_heuristically(request: str) -> tuple[str | None, str]:
        """Deterministic no-LLM parse: a ticker-shaped non-stopword token + timeframe."""
        tokens = request.replace(",", " ").split()
        timeframe = "1d"
        symbol: str | None = None
        for tok in tokens:
            low = tok.strip().lower()
            if low in _TIMEFRAMES:
                timeframe = low
                continue
            if low in _TF_WORDS:
                timeframe = _TF_WORDS[low]
                continue
            if symbol is None and _TICKER_RE.match(tok) and low not in _STOPWORDS:
                symbol = tok.strip().upper()
        return symbol, timeframe

    @staticmethod
    def _fallback(report: TradingReport) -> str:
        """A deterministic, number-faithful summary of the report (no LLM)."""
        rec = report.recommendation.value.upper()
        direction = report.direction.value
        confidence = report.confidence.value
        actionable = "actionable" if report.is_actionable else "not actionable"
        lines = [
            f"{report.instrument.key} ({report.analysis.timeframe_value}): "
            f"{rec} -- a '{direction}' lean at {confidence} confidence, "
            f"{actionable}.",
        ]
        if report.limitations:
            lines.append("Limitations: " + "; ".join(report.limitations[:3]))
        lines.append(
            "Probabilities are estimates, not guarantees; this is analysis, "
            "not advice."
        )
        return " ".join(lines)
