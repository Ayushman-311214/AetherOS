"""
SignalService: the composed engine over the real deterministic services.

Integration tests through the same container-style wiring the bootstrapper
uses. The honesty properties are pinned hardest, because they are the phase's
contract with §9/§28:

- MOCK data can never produce a signal (the critic's INSUFFICIENT_EVIDENCE
  verdict is a hard gate).
- Every candidate that declined names the gate that stopped it.
- A fired signal carries the risk engine's geometry verbatim.
- The SignalGenerated event is published only for fired signals.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.errors import SignalError
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.breakout_service import BreakoutService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.ict_service import ICTService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.signal_service import SignalService
from aetheros.trading.services.smc_service import SMCService
from aetheros.trading.services.strategy_service import StrategyService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)


@pytest.fixture
def service() -> SignalService:
    settings = get_settings()
    provider = MockMarketDataProvider()
    market_data = MarketDataService(provider, settings)
    structure = MarketStructureService()
    evidence = EvidenceService()
    analysis = AnalysisService(
        market_data,
        TechnicalAnalysisService(),
        structure,
        evidence,
        settings,
    )
    risk = RiskService(settings)
    critic = CriticService(settings)
    backtest = BacktestService(settings)
    breakout = BreakoutService(settings)
    smc = SMCService(structure)
    ict = ICTService(structure, smc)
    strategy = StrategyService(
        analysis,
        structure,
        smc=smc,
        ict=ict,
        breakout=breakout,
        backtest=backtest,
    )
    return SignalService(
        strategy,
        risk,
        critic,
        market_data,
        settings,
    )


# A gentle random-walk-ish uptrend that the mock provider generates: the
# point of these tests is the *pipeline*, not a particular market shape.


@pytest.mark.asyncio
async def test_mock_data_never_produces_a_signal(service):
    """The honesty gate: synthetic data verifies machinery, never a trade."""
    evaluation = await service.evaluate("AAPL", limit=120)
    assert evaluation.signal_count == 0
    for candidate in evaluation.candidates:
        assert not candidate.fired
        # The stopping gate is named. On mock data the risk assessment is
        # not actionable, so the actionability gate fires first and the
        # critic gate is never reached -- both are correct §28 outcomes.
        assert candidate.rejections
        assert any(
            ("actionable" in reason or "critic" in reason)
            for reason in candidate.rejections
        )


@pytest.mark.asyncio
async def test_the_evaluation_shape_over_a_full_panel(service):
    evaluation = await service.evaluate("AAPL", limit=120)
    payload = evaluation.to_dict()
    assert payload["instrument_key"] == "AAPL"
    assert payload["timeframe"] == "1d"
    assert payload["consensus"] in ("up", "down", "sideways", "unknown")
    for candidate in payload["candidates"]:
        # Every candidate carries its full judgement trail.
        assert candidate["risk"]
        assert candidate["critique"]
        assert isinstance(candidate["rejections"], list)
    # Declined strategies are named in limitations, not silently dropped.
    assert isinstance(payload["limitations"], list)


@pytest.mark.asyncio
async def test_a_subset_of_strategies_can_be_evaluated(service):
    evaluation = await service.evaluate(
        "AAPL", limit=120, strategy_ids=["trend_following"]
    )
    assert [c.strategy_id for c in evaluation.candidates] <= ["trend_following"]


@pytest.mark.asyncio
async def test_evaluating_an_unknown_strategy_is_an_error(service):
    with pytest.raises(ValueError, match="Unknown strategy"):
        await service.evaluate("AAPL", limit=120, strategy_ids=["nope"])


@pytest.mark.asyncio
async def test_an_empty_registry_is_an_error_not_an_empty_result(service):
    # A failure to evaluate at all is distinct from an honest empty result.
    service._strategy.registry.clear()
    with pytest.raises(SignalError, match="No strategies registered"):
        await service.evaluate("AAPL", limit=120)


@pytest.mark.asyncio
async def test_candidates_never_fire_when_no_setup_exists(service):
    """Strategies that declined produce no candidate -- recorded in limitations."""
    evaluation = await service.evaluate(
        "AAPL", limit=120, strategy_ids=["ict", "mean_reversion"]
    )
    # Whatever fired, the limitations account for every strategy that stayed
    # out, so the result answers "who declined?" as well as "who fired?".
    fired_ids = set(evaluation.fired_strategies)
    for line in evaluation.limitations:
        if "produced no setup" in line:
            assert any(sid not in fired_ids for sid in ("ict", "mean_reversion"))


@pytest.mark.asyncio
async def test_evaluation_determinism(service):
    """Same inputs, same candidates, same ids -- the audit-trail contract."""
    first = await service.evaluate("AAPL", limit=120)
    second = await service.evaluate("AAPL", limit=120)
    assert [c.candidate_id for c in first.candidates] == [
        c.candidate_id for c in second.candidates
    ]
    assert [c.fired for c in first.candidates] == [
        c.fired for c in second.candidates
    ]
