"""
Execution-policy service (spec Phase 26 -- "Policy + Execution Safety").

:class:`ExecutionPolicyService` is the first gate on the §9 execution path:

    Decision ─► **Policy** ─► Risk Validation ─► Execution Validation ─► Broker

It judges a fully-formed :class:`ExecutionRequest` against the deployment's
policy -- the trading mode, the per-trade risk cap, the venue/instrument
/strategy allow-lists, and (for live orders) an explicit confirmation -- and
returns a deterministic :class:`PolicyVerdict`. It computes no geometry and
sizes nothing: those are the risk layer's job, already done by the time a
request exists. Policy only answers "is this *kind* of order, to this venue,
in this mode, permitted at all?".

The gate is fail-safe by construction:

* The default mode is PAPER, so a live venue is blocked unless the operator
  deliberately switches to LIVE *and* confirms the specific order.
* An unknown / unparseable mode is treated as the most restrictive
  (ANALYSIS_ONLY), never silently permitted.
* An empty allow-list means "allow all" (the common single-desk case), but a
  non-empty list is strict: anything outside it is refused.

Nothing here submits an order or touches a broker; it returns a verdict for a
caller (the execution engine, the trading API) to honour.
"""

from __future__ import annotations

from ...config.settings import Settings
from ...core.logging import get_logger
from ..brokers.base import BrokerProvider
from ..domain.enums import TradingMode
from ..domain.execution import ExecutionRequest
from ..domain.policy import PolicyCheck, PolicyVerdict

logger = get_logger("trading.policy")


def _parse_allow_list(raw: str) -> frozenset[str]:
    """Comma-separated string → a set of upper-cased, stripped tokens."""
    return frozenset(
        token.strip().upper() for token in raw.split(",") if token.strip()
    )


def _parse_mode(raw: str) -> TradingMode:
    """Map a configured mode string to the enum, failing safe to the most
    restrictive mode when the value is unrecognised."""
    try:
        return TradingMode(raw.strip().lower())
    except ValueError:
        logger.warning(
            "Unrecognised TRADING_MODE %r; failing safe to analysis_only.", raw
        )
        return TradingMode.ANALYSIS_ONLY


class ExecutionPolicyService:
    """Deterministic execution-admission policy gate (spec Phase 26)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def mode(self) -> TradingMode:
        """The configured trading mode (fail-safe on an unknown value)."""
        return _parse_mode(self._settings.TRADING_MODE)

    def evaluate(
        self,
        request: ExecutionRequest,
        broker: BrokerProvider,
        *,
        confirmed: bool = False,
    ) -> PolicyVerdict:
        """
        Judge one request against the policy for the venue it targets.

        Pure: the same request, broker and settings always produce the same
        verdict. ``confirmed`` is the caller's explicit go-ahead for a live
        order; it is only consulted in LIVE mode and only when confirmation is
        required by configuration.
        """
        mode = self.mode
        checks = (
            self._check_mode(mode, broker),
            self._check_live_confirmation(mode, broker, confirmed),
            self._check_max_risk(request),
            self._check_allowed_broker(broker),
            self._check_allowed_instrument(request),
            self._check_allowed_strategy(request),
        )
        allowed = all(check.passed for check in checks)
        verdict = PolicyVerdict(
            allowed=allowed,
            mode=mode,
            broker_name=broker.name,
            checks=checks,
        )
        if not allowed:
            logger.warning(
                "Execution policy denied %s to '%s': %s",
                request.request_id,
                broker.name,
                verdict.reason,
            )
        return verdict

    # ------------------------------------------------------------------
    # Individual rules
    # ------------------------------------------------------------------

    @staticmethod
    def _check_mode(mode: TradingMode, broker: BrokerProvider) -> PolicyCheck:
        """The trading mode governs which venues may be reached at all."""
        if mode is TradingMode.ANALYSIS_ONLY:
            return PolicyCheck(
                name="mode",
                passed=False,
                reason=(
                    "Trading mode is analysis_only; no order may be submitted "
                    "to any venue."
                ),
            )
        if mode is TradingMode.PAPER:
            if broker.is_paper:
                return PolicyCheck(
                    name="mode",
                    passed=True,
                    reason="Paper mode permits the paper venue.",
                )
            return PolicyCheck(
                name="mode",
                passed=False,
                reason=(
                    f"Trading mode is paper; the live venue '{broker.name}' is "
                    "blocked. Only a paper venue may be used."
                ),
            )
        # LIVE: both live and paper venues are permitted at the mode gate; a
        # live order still faces the confirmation rule below.
        return PolicyCheck(
            name="mode",
            passed=True,
            reason=f"Live mode permits the venue '{broker.name}'.",
        )

    def _check_live_confirmation(
        self, mode: TradingMode, broker: BrokerProvider, confirmed: bool
    ) -> PolicyCheck:
        """A live order needs an explicit confirmation when configured."""
        required = self._settings.TRADING_POLICY_REQUIRE_LIVE_CONFIRMATION
        is_live_order = mode is TradingMode.LIVE and not broker.is_paper
        if not is_live_order:
            return PolicyCheck(
                name="live_confirmation",
                passed=True,
                reason="Not a live order; no confirmation required.",
            )
        if not required:
            return PolicyCheck(
                name="live_confirmation",
                passed=True,
                reason="Live confirmation is not required by configuration.",
            )
        if confirmed:
            return PolicyCheck(
                name="live_confirmation",
                passed=True,
                reason="Live order explicitly confirmed by the caller.",
            )
        return PolicyCheck(
            name="live_confirmation",
            passed=False,
            reason=(
                "A live order requires explicit confirmation and none was "
                "given; it is refused."
            ),
        )

    def _check_max_risk(self, request: ExecutionRequest) -> PolicyCheck:
        """Per-trade risk must not exceed the configured cap."""
        cap = self._settings.TRADING_POLICY_MAX_RISK_PER_TRADE_PCT
        if cap <= 0:
            return PolicyCheck(
                name="max_risk_per_trade",
                passed=True,
                reason="Per-trade risk cap is disabled (0).",
            )
        risk_pct = request.risk_pct
        if risk_pct is None:
            # An unknown per-trade risk cannot be shown to be inside the cap,
            # so it fails closed -- a gate that cannot see its input is no gate.
            return PolicyCheck(
                name="max_risk_per_trade",
                passed=False,
                reason=(
                    "The request carries no risk_pct; the per-trade risk cap "
                    f"of {cap:g}% cannot be verified, so it fails closed."
                ),
            )
        if risk_pct > cap:
            return PolicyCheck(
                name="max_risk_per_trade",
                passed=False,
                reason=(
                    f"Per-trade risk {risk_pct:g}% exceeds the {cap:g}% cap."
                ),
            )
        return PolicyCheck(
            name="max_risk_per_trade",
            passed=True,
            reason=f"Per-trade risk {risk_pct:g}% is inside the {cap:g}% cap.",
        )

    def _check_allowed_broker(self, broker: BrokerProvider) -> PolicyCheck:
        allowed = _parse_allow_list(self._settings.TRADING_POLICY_ALLOWED_BROKERS)
        if not allowed:
            return PolicyCheck(
                name="allowed_broker",
                passed=True,
                reason="No broker allow-list configured; all venues permitted.",
            )
        if broker.name.strip().upper() in allowed:
            return PolicyCheck(
                name="allowed_broker",
                passed=True,
                reason=f"Venue '{broker.name}' is on the broker allow-list.",
            )
        return PolicyCheck(
            name="allowed_broker",
            passed=False,
            reason=f"Venue '{broker.name}' is not on the broker allow-list.",
        )

    def _check_allowed_instrument(self, request: ExecutionRequest) -> PolicyCheck:
        allowed = _parse_allow_list(
            self._settings.TRADING_POLICY_ALLOWED_INSTRUMENTS
        )
        if not allowed:
            return PolicyCheck(
                name="allowed_instrument",
                passed=True,
                reason="No instrument allow-list configured; all permitted.",
            )
        # Match on either the canonical EXCHANGE:SYMBOL key or the bare symbol,
        # so an operator can list "RELIANCE" without pinning the exchange.
        key = request.instrument.key.strip().upper()
        symbol = request.instrument.symbol.strip().upper()
        if key in allowed or symbol in allowed:
            return PolicyCheck(
                name="allowed_instrument",
                passed=True,
                reason=f"Instrument '{key}' is on the instrument allow-list.",
            )
        return PolicyCheck(
            name="allowed_instrument",
            passed=False,
            reason=f"Instrument '{key}' is not on the instrument allow-list.",
        )

    def _check_allowed_strategy(self, request: ExecutionRequest) -> PolicyCheck:
        allowed = _parse_allow_list(
            self._settings.TRADING_POLICY_ALLOWED_STRATEGIES
        )
        if not allowed:
            return PolicyCheck(
                name="allowed_strategy",
                passed=True,
                reason="No strategy allow-list configured; all permitted.",
            )
        if request.strategy_id.strip().upper() in allowed:
            return PolicyCheck(
                name="allowed_strategy",
                passed=True,
                reason=(
                    f"Strategy '{request.strategy_id}' is on the strategy "
                    "allow-list."
                ),
            )
        return PolicyCheck(
            name="allowed_strategy",
            passed=False,
            reason=(
                f"Strategy '{request.strategy_id}' is not on the strategy "
                "allow-list."
            ),
        )
