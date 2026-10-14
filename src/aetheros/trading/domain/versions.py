"""
Component-version manifest (spec section 16 -- versioning & provenance).

A decision can only be *reproduced* (and its correctness only audited) when the
versions of everything that shaped it are pinned: the data source, the
indicator set, the SMC/ICT structure rules, the strategy rule book, the
probability model + its calibrator, the risk/policy parameters, the critic
thresholds, and the orchestrator's own pipeline. Section 16 requires every such
component that can change decision behavior to carry a version so a change in
decision behavior is traceable to a specific upgrade.

:class:`ComponentVersions` is the single manifest those pins collect into. It
is *not* a second configuration system -- the numeric values still live in
``config.settings`` -- it is the *label* of the rule set currently active, so a
report/decision/snapshot can answer "which revision produced me?". A version
bump in code (a renamed rule, a recalibrated model, a re-tuned ATR stop) is the
one place a maintainer edits, and every record produced afterwards inherits it
automatically via :func:`default_versions`.

Two honesty rules:

* **Versions are declared, not guessed.** Each field is a frozen constant the
  owning layer maintains; there is no attempt to "detect" a version from
  behaviour. ``data_version`` is the *schema/format* of the data inputs
  (``MarketData``/``Candle``/``OrderBook``) so a stored record can tell whether
  it was written under the same data contract, not the data itself (the actual
  data is fingerprinted separately in the snapshot).
* **A version is a label, not a secret.** The manifest carries no provider
  credentials and no environment values; the ``config_version`` is a *logical*
  revision of the trading knob-set, not the resolved values themselves (those
  stay in ``Settings`` and are never dumped into a record verbatim).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ComponentVersions:
    """
    The pinned versions of every component that can change a decision.

    All fields are free-form ``str`` so each layer owns its own scheme
    (``name/semver`` for models, ``vN`` for rule sets, a date for data schema).
    ``to_dict`` is what a snapshot/report embeds.
    """

    #: The deterministic pipeline / orchestrator revision.
    pipeline: str
    #: The indicator set revision (SMA/EMA/RSI/MACD/ATR/Bollinger/SuperTrend/ADX).
    indicators: str
    #: The market-structure + SMC/ICT rule-set revision.
    smc_ict_rules: str
    #: The strategy rule-book revision (the panel of RuleBasedStrategy rules).
    strategy_rules: str
    #: The probability model revision (name/version of the calibrated estimator).
    probability_model: str
    #: The calibration scheme revision (Platt/isotonic map).
    calibration: str
    #: The risk-engine revision (ATR stop/target/R:R geometry).
    risk_model: str
    #: The critic check-set revision (which gates run and their thresholds).
    critic_rules: str
    #: The policy/risk-limit revision (daily-loss, exposure, instrument caps).
    risk_policy: str
    #: The decision-assembly revision (how report -> decision -> action projects).
    decision_engine: str
    #: The data-input schema revision (MarketData/Candle/OrderBook contract).
    data_schema: str
    #: The logical config revision of the trading knob-set (Settings).
    config: str
    #: The market-data provider lineage (source name + tier, e.g. "yahoo/primary").
    provider: str

    def to_dict(self) -> dict[str, str]:
        return {
            "pipeline": self.pipeline,
            "indicators": self.indicators,
            "smc_ict_rules": self.smc_ict_rules,
            "strategy_rules": self.strategy_rules,
            "probability_model": self.probability_model,
            "calibration": self.calibration,
            "risk_model": self.risk_model,
            "critic_rules": self.critic_rules,
            "risk_policy": self.risk_policy,
            "decision_engine": self.decision_engine,
            "data_schema": self.data_schema,
            "config": self.config,
            "provider": self.provider,
        }


#: The current logical revision of each component. Bump the entry (and only the
#: entry) whose behaviour changed; every record produced afterwards inherits it.
_PIPELINE = "deterministic-core/1.0"
_INDICATORS = "indicators-core/1.0"
_SMC_ICT_RULES = "smc-ict/1.0"
_STRATEGY_RULES = "strategy-panel/1.0"
_PROBABILITY_MODEL = "logistic_momentum/1.0.0"
_CALIBRATION = "platt/1.0"
_RISK_MODEL = "atr-structural/1.0"
_CRITIC_RULES = "critic-gates/1.0"
_RISK_POLICY = "risk-limits/1.0"
_DECISION_ENGINE = "decision/1.0"
_DATA_SCHEMA = "ohlcv-v1"
_CONFIG = "trading-knobs/1.0"
_PROVIDER = "unknown"


def default_versions(provider: str = _PROVIDER) -> ComponentVersions:
    """
    The manifest for the components wired into this build.

    ``provider`` names the market-data source lineage (the only value that can
    vary at runtime); everything else is the compile-time revision of the rule
    set. Kept as a small pure function so a later component-level version bump
    is a one-line edit and a snapshot always reads the *current* manifest.
    """
    return ComponentVersions(
        pipeline=_PIPELINE,
        indicators=_INDICATORS,
        smc_ict_rules=_SMC_ICT_RULES,
        strategy_rules=_STRATEGY_RULES,
        probability_model=_PROBABILITY_MODEL,
        calibration=_CALIBRATION,
        risk_model=_RISK_MODEL,
        critic_rules=_CRITIC_RULES,
        risk_policy=_RISK_POLICY,
        decision_engine=_DECISION_ENGINE,
        data_schema=_DATA_SCHEMA,
        config=_CONFIG,
        provider=provider,
    )
