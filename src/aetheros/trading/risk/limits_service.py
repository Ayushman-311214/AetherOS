"""
Account-level risk-limit enforcement (spec Phase 9 -- "daily loss limits,
maximum exposure").

The spec's Risk Manager lists six responsibilities. Four of them -- position
sizing, stop-loss calculation, take-profit calculation, risk/reward -- are
already the deterministic output of
:class:`~aetheros.trading.services.risk_service.RiskService`, and gross
exposure is already capped at *allocation* time by
:class:`~aetheros.trading.services.portfolio_service.PortfolioRiskService`.
This module adds the genuinely missing piece: an *admission gate* that
answers, before any new position is opened, whether the account as it stands
is inside its configured boundaries.

The gate is deterministic and fail-closed:

- **Daily loss limit** -- realised PnL today, as a fraction of equity, must
  not be at or below ``-TRADING_RISK_DAILY_LOSS_PCT``. A day already that
  far negative stops new trading, whatever the setup looks like.
- **Maximum exposure** -- open notional exposure, as a fraction of equity,
  must not exceed ``TRADING_RISK_MAX_EXPOSURE_PCT``.

An input the caller could not measure (PnL or exposure unknown) fails the
check rather than passing it: a gate that cannot see its own input is not a
gate. The verdict carries the numbers it was judged from so the refusal can
be audited by hand, and a breach publishes :class:`RiskLimitReached` -- the
event the spec's event vocabulary already reserves for exactly this.
"""

from __future__ import annotations

import asyncio

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.risk_limits import (
    AccountSnapshot,
    RiskLimitOutcome,
    RiskLimitsVerdict,
)
from ..events import RiskLimitReached

logger = get_logger("trading.risk_limits")

#: Outcome name for the daily realised-loss check.
DAILY_LOSS = "daily_loss"

#: Outcome name for the open-exposure check.
MAX_EXPOSURE = "max_exposure"


class RiskLimitsService:
    """Deterministic account-level risk-limit admission gate."""

    def __init__(
        self,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._settings = settings
        self._event_bus = event_bus

    def check(self, snapshot: AccountSnapshot) -> RiskLimitsVerdict:
        """
        Judge one account snapshot against both configured limits.

        Pure: the same snapshot and settings always produce the same verdict.
        Side effects (the breach event) happen only when a limit is actually
        breached.
        """
        daily_pct = self._settings.TRADING_RISK_DAILY_LOSS_PCT
        exposure_pct = self._settings.TRADING_RISK_MAX_EXPOSURE_PCT

        outcomes = (
            self._daily_loss(snapshot, daily_pct),
            self._max_exposure(snapshot, exposure_pct),
        )
        verdict = RiskLimitsVerdict(
            outcomes=outcomes,
            equity=snapshot.equity,
            captured_at=snapshot.captured_at,
        )
        for outcome in verdict.breached:
            self._log_and_emit(verdict, outcome)
        return verdict

    # ------------------------------------------------------------------

    @staticmethod
    def _daily_loss(
        snapshot: AccountSnapshot, limit_pct: float
    ) -> RiskLimitOutcome:
        """Realised PnL today must not be at or below -limit as a fraction."""
        if snapshot.realised_pnl_today is None:
            return RiskLimitOutcome(
                limit_name=DAILY_LOSS,
                passed=False,
                reason=(
                    "Realised PnL for the day is unknown; the daily-loss limit "
                    "cannot be verified, so it fails closed."
                ),
                observed=None,
                limit=limit_pct,
            )
        observed = snapshot.realised_pnl_today / snapshot.equity
        if observed <= -limit_pct:
            return RiskLimitOutcome(
                limit_name=DAILY_LOSS,
                passed=False,
                reason=(
                    f"Realised PnL today is {snapshot.realised_pnl_today:.2f} "
                    f"({observed:.2%} of equity), at or beyond the "
                    f"-{limit_pct:.2%} daily loss limit."
                ),
                observed=round(observed, 6),
                limit=limit_pct,
            )
        return RiskLimitOutcome(
            limit_name=DAILY_LOSS,
            passed=True,
            reason=(
                f"Realised PnL today is {observed:.2%} of equity, inside the "
                f"-{limit_pct:.2%} daily loss limit."
            ),
            observed=round(observed, 6),
            limit=limit_pct,
        )

    @staticmethod
    def _max_exposure(
        snapshot: AccountSnapshot, limit_pct: float
    ) -> RiskLimitOutcome:
        """Open notional exposure must not exceed the cap as a fraction."""
        if snapshot.open_exposure_notional is None:
            return RiskLimitOutcome(
                limit_name=MAX_EXPOSURE,
                passed=False,
                reason=(
                    "Open exposure is unknown; the maximum-exposure limit "
                    "cannot be verified, so it fails closed."
                ),
                observed=None,
                limit=limit_pct,
            )
        observed = snapshot.open_exposure_notional / snapshot.equity
        if observed > limit_pct:
            return RiskLimitOutcome(
                limit_name=MAX_EXPOSURE,
                passed=False,
                reason=(
                    f"Open exposure is {snapshot.open_exposure_notional:.2f} "
                    f"({observed:.2%} of equity), beyond the {limit_pct:.2%} "
                    "maximum."
                ),
                observed=round(observed, 6),
                limit=limit_pct,
            )
        return RiskLimitOutcome(
            limit_name=MAX_EXPOSURE,
            passed=True,
            reason=(
                f"Open exposure is {observed:.2%} of equity, inside the "
                f"{limit_pct:.2%} maximum."
            ),
            observed=round(observed, 6),
            limit=limit_pct,
        )

    # ------------------------------------------------------------------

    def _log_and_emit(
        self, verdict: RiskLimitsVerdict, outcome: RiskLimitOutcome
    ) -> None:
        logger.warning(
            "Risk limit breached: %s -- %s",
            outcome.limit_name,
            outcome.reason,
        )
        if self._event_bus is None:
            return
        try:
            # Publish is async on the shared bus; schedule it without blocking
            # this synchronous gate (the breach is already logged, so an
            # event-delivery failure loses nothing but the notification).
            asyncio.get_running_loop().create_task(
                self._event_bus.publish(
                    RiskLimitReached(
                        limit_name=outcome.limit_name,
                        observed_value=outcome.observed or 0.0,
                        limit_value=outcome.limit or 0.0,
                        reason=outcome.reason,
                    )
                )
            )
        except RuntimeError:
            # No running loop (a synchronous caller): log already done; the
            # verdict itself is the durable record of the breach.
            pass
        except Exception:
            logger.exception("Failed to publish RiskLimitReached")
