"""
Trading alerts (spec Phase 23).

The point of this phase is a decoupling, so the tests prove the decoupling:
rules turn events into alerts knowing nothing about delivery, the router fans
an alert to providers knowing nothing about why it exists, and an unroutable
or dead channel is reported rather than dropped. Honesty carries through --
an alert from a mock or unreliable event is never raised.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.trading.alerts import (
    Alert,
    AlertKind,
    AlertRouter,
    AlertService,
    AlertSeverity,
    CollectingDeliveryProvider,
    DeliveryChannel,
    DeliveryProvider,
    DeliveryResult,
    LogDeliveryProvider,
    rules,
)
from aetheros.trading.events import (
    MarketEventsDetected,
    MarketRegimeDetected,
    NewsSentimentAnalyzed,
    RiskLimitReached,
    SignalGenerated,
)

# ==============================================================
# Alert domain
# ==============================================================


def test_alert_id_is_content_addressed_and_ignores_time() -> None:
    a = Alert(
        kind=AlertKind.SIGNAL,
        severity=AlertSeverity.WARNING,
        title="BUY signal: AAPL",
        body="A bullish buy signal was generated.",
        instrument_key="AAPL",
    )
    b = Alert(
        kind=AlertKind.SIGNAL,
        severity=AlertSeverity.WARNING,
        title="BUY signal: AAPL",
        body="A bullish buy signal was generated.",
        instrument_key="AAPL",
    )
    assert a.alert_id == b.alert_id
    assert a.alert_id.startswith("alert_")


def test_alert_rejects_empty_title_or_body() -> None:
    with pytest.raises(ValueError):
        Alert(
            kind=AlertKind.PRICE,
            severity=AlertSeverity.INFO,
            title="   ",
            body="x",
        )
    with pytest.raises(ValueError):
        Alert(
            kind=AlertKind.PRICE,
            severity=AlertSeverity.INFO,
            title="x",
            body="",
        )


def test_severity_rank_orders_low_to_high() -> None:
    assert AlertSeverity.INFO.rank < AlertSeverity.WARNING.rank
    assert AlertSeverity.WARNING.rank < AlertSeverity.CRITICAL.rank


def test_alert_to_dict_is_json_shaped() -> None:
    alert = Alert(
        kind=AlertKind.NEWS,
        severity=AlertSeverity.INFO,
        title="t",
        body="b",
        channels=(DeliveryChannel.DESKTOP, DeliveryChannel.EMAIL),
    )
    payload = alert.to_dict()
    assert payload["kind"] == "news"
    assert payload["channels"] == ["desktop", "email"]
    assert payload["is_reliable"] is True


# ==============================================================
# Rules: events -> alerts, honesty gates
# ==============================================================


def test_signal_rule_maps_confidence_to_severity() -> None:
    high = rules.signal_alert(
        SignalGenerated(
            signal_id="s1",
            instrument_key="AAPL",
            action="buy",
            direction="bullish",
            confidence="high",
            risk="medium",
        )
    )
    assert high.kind == AlertKind.SIGNAL
    assert high.severity == AlertSeverity.CRITICAL
    low = rules.signal_alert(
        SignalGenerated(signal_id="s2", instrument_key="X", action="sell",
                        direction="bearish", confidence="low", risk="low")
    )
    assert low.severity == AlertSeverity.INFO


def test_news_rule_fires_only_on_reliable_directional_reads() -> None:
    bullish = rules.news_alert(
        NewsSentimentAnalyzed(
            instrument_key="AAPL",
            direction="bullish",
            sentiment_score=0.7,
            item_count=5,
            positive_count=4,
            negative_count=1,
            is_reliable=True,
            source_tier="secondary",
        )
    )
    assert bullish is not None
    assert bullish.severity == AlertSeverity.WARNING

    # Neutral -> no alert.
    assert rules.news_alert(
        NewsSentimentAnalyzed(instrument_key="X", direction="neutral",
                              is_reliable=True, source_tier="secondary")
    ) is None
    # Unreliable -> no alert.
    assert rules.news_alert(
        NewsSentimentAnalyzed(instrument_key="X", direction="bullish",
                              is_reliable=False, source_tier="secondary")
    ) is None
    # Mock source -> no alert even if reliable.
    assert rules.news_alert(
        NewsSentimentAnalyzed(instrument_key="X", direction="bullish",
                              is_reliable=True, source_tier="mock")
    ) is None


def test_risk_rule_is_always_critical() -> None:
    alert = rules.risk_alert(
        RiskLimitReached(
            limit_name="daily_loss",
            observed_value=1200.0,
            limit_value=1000.0,
            instrument_key="AAPL",
            reason="daily loss budget exceeded",
        )
    )
    assert alert.kind == AlertKind.PORTFOLIO
    assert alert.severity == AlertSeverity.CRITICAL
    assert "daily_loss" in alert.title


def test_event_risk_rule_needs_a_reliable_high_impact_event() -> None:
    hit = rules.event_risk_alert(
        MarketEventsDetected(
            instrument_key="AAPL",
            horizon_days=7,
            event_count=1,
            has_high_impact=True,
            next_event_type="macro",
            next_event_days=1.5,
            next_high_impact_kind="cpi",
            is_reliable=True,
            source_tier="secondary",
        )
    )
    assert hit is not None
    assert hit.kind == AlertKind.PATTERN
    assert "cpi" in hit.body.lower()

    # No high-impact event -> nothing.
    assert rules.event_risk_alert(
        MarketEventsDetected(instrument_key="X", has_high_impact=False,
                             is_reliable=True, source_tier="secondary")
    ) is None
    # Mock -> nothing.
    assert rules.event_risk_alert(
        MarketEventsDetected(instrument_key="X", has_high_impact=True,
                             is_reliable=True, source_tier="mock")
    ) is None


def test_regime_rule_fires_only_on_a_reliable_trend() -> None:
    trend = rules.regime_alert(
        MarketRegimeDetected(instrument_key="AAPL", timeframe="1d",
                             regime="trending_up", adx=32.0,
                             is_reliable=True, source_tier="secondary")
    )
    assert trend is not None
    assert trend.kind == AlertKind.PATTERN
    # Ranging -> nothing.
    assert rules.regime_alert(
        MarketRegimeDetected(instrument_key="X", regime="ranging",
                             is_reliable=True, source_tier="secondary")
    ) is None


def test_price_rule_builds_a_threshold_alert() -> None:
    alert = rules.price_alert(
        instrument_key="AAPL", price=201.5, threshold=200.0, direction="above"
    )
    assert alert.kind == AlertKind.PRICE
    assert alert.severity == AlertSeverity.WARNING
    assert "above" in alert.body


# ==============================================================
# Router: Alert -> AlertRouter -> DeliveryProvider
# ==============================================================


def _alert(channels: tuple[DeliveryChannel, ...]) -> Alert:
    return Alert(
        kind=AlertKind.SIGNAL,
        severity=AlertSeverity.INFO,
        title="t",
        body="b",
        channels=channels,
    )


@pytest.mark.asyncio
async def test_router_delivers_to_each_named_channel() -> None:
    router = AlertRouter(default_channel=None)
    desktop = CollectingDeliveryProvider(DeliveryChannel.DESKTOP)
    email = CollectingDeliveryProvider(DeliveryChannel.EMAIL)
    router.register(desktop)
    router.register(email)

    results = await router.route(
        _alert((DeliveryChannel.DESKTOP, DeliveryChannel.EMAIL))
    )
    assert {r.channel for r in results} == {
        DeliveryChannel.DESKTOP,
        DeliveryChannel.EMAIL,
    }
    assert all(r.delivered for r in results)
    assert len(desktop.alerts) == 1
    assert len(email.alerts) == 1


@pytest.mark.asyncio
async def test_router_reports_an_unroutable_channel_instead_of_dropping() -> None:
    router = AlertRouter(default_channel=None)
    router.register(CollectingDeliveryProvider(DeliveryChannel.DESKTOP))

    results = await router.route(
        _alert((DeliveryChannel.DESKTOP, DeliveryChannel.TELEGRAM))
    )
    by_channel = {r.channel: r for r in results}
    assert by_channel[DeliveryChannel.DESKTOP].delivered is True
    telegram = by_channel[DeliveryChannel.TELEGRAM]
    assert telegram.delivered is False
    assert "no provider" in telegram.detail


@pytest.mark.asyncio
async def test_router_falls_back_to_default_channel() -> None:
    router = AlertRouter(default_channel=DeliveryChannel.DESKTOP)
    collector = CollectingDeliveryProvider(DeliveryChannel.DESKTOP)
    router.register(collector)

    results = await router.route(_alert(()))
    assert len(results) == 1
    assert results[0].channel == DeliveryChannel.DESKTOP
    assert len(collector.alerts) == 1


@pytest.mark.asyncio
async def test_router_routes_nowhere_when_no_channel_and_no_default() -> None:
    router = AlertRouter(default_channel=None)
    assert await router.route(_alert(())) == ()


@pytest.mark.asyncio
async def test_a_dead_provider_does_not_stop_the_others() -> None:
    class Boom(DeliveryProvider):
        channel = DeliveryChannel.EMAIL

        @property
        def name(self) -> str:
            return "boom"

        async def deliver(self, alert: Alert) -> DeliveryResult:
            raise RuntimeError("smtp down")

    router = AlertRouter(default_channel=None)
    desktop = CollectingDeliveryProvider(DeliveryChannel.DESKTOP)
    router.register(desktop)
    router.register(Boom())

    results = await router.route(
        _alert((DeliveryChannel.EMAIL, DeliveryChannel.DESKTOP))
    )
    by_channel = {r.channel: r for r in results}
    assert by_channel[DeliveryChannel.EMAIL].delivered is False
    assert "raised" in by_channel[DeliveryChannel.EMAIL].detail
    assert by_channel[DeliveryChannel.DESKTOP].delivered is True
    assert len(desktop.alerts) == 1


@pytest.mark.asyncio
async def test_log_provider_always_delivers() -> None:
    router = AlertRouter(default_channel=None)
    router.register(LogDeliveryProvider())
    results = await router.route(_alert((DeliveryChannel.DESKTOP,)))
    assert results[0].delivered is True
    assert results[0].provider == "log"


# ==============================================================
# Service: event bus -> generation -> routing, fully decoupled
# ==============================================================


def _service(bus: EventBus, collector: CollectingDeliveryProvider) -> AlertService:
    router = AlertRouter(default_channel=None)
    router.register(collector)
    return AlertService(
        router,
        get_settings(),
        event_bus=bus,
        default_channels=(collector.channel,),
    )


@pytest.mark.asyncio
async def test_service_generates_and_routes_an_alert_from_a_published_event() -> None:
    bus = EventBus()
    collector = CollectingDeliveryProvider(DeliveryChannel.DESKTOP)
    service = _service(bus, collector)
    await service.start()
    try:
        await bus.publish(
            SignalGenerated(
                signal_id="s1",
                instrument_key="AAPL",
                action="buy",
                direction="bullish",
                confidence="high",
                risk="medium",
            )
        )
    finally:
        await service.stop()

    assert len(collector.alerts) == 1
    assert collector.alerts[0].kind == AlertKind.SIGNAL
    recent = service.recent()
    assert len(recent) == 1


@pytest.mark.asyncio
async def test_service_does_not_raise_an_alert_for_a_mock_news_event() -> None:
    bus = EventBus()
    collector = CollectingDeliveryProvider(DeliveryChannel.DESKTOP)
    service = _service(bus, collector)
    await service.start()
    try:
        await bus.publish(
            NewsSentimentAnalyzed(
                instrument_key="AAPL",
                direction="bullish",
                sentiment_score=0.9,
                is_reliable=True,
                source_tier="mock",
            )
        )
    finally:
        await service.stop()
    assert collector.alerts == ()


@pytest.mark.asyncio
async def test_service_stop_unsubscribes() -> None:
    bus = EventBus()
    collector = CollectingDeliveryProvider(DeliveryChannel.DESKTOP)
    service = _service(bus, collector)
    await service.start()
    await service.stop()
    await bus.publish(
        RiskLimitReached(limit_name="x", observed_value=2, limit_value=1)
    )
    assert collector.alerts == ()


@pytest.mark.asyncio
async def test_raise_alert_routes_a_prebuilt_alert() -> None:
    bus = EventBus()
    collector = CollectingDeliveryProvider(DeliveryChannel.DESKTOP)
    service = _service(bus, collector)
    alert = rules.price_alert(
        instrument_key="AAPL",
        price=201.0,
        threshold=200.0,
        direction="above",
        channels=(DeliveryChannel.DESKTOP,),
    )
    results = await service.raise_alert(alert)
    assert results[0].delivered is True
    assert len(collector.alerts) == 1
    assert service.recent()[-1].kind == AlertKind.PRICE


@pytest.mark.asyncio
async def test_a_failing_rule_never_breaks_the_producer() -> None:
    # The service must swallow a generation error: a bad alert must not stop
    # the event from reaching other subscribers or crash the publisher.
    bus = EventBus()
    collector = CollectingDeliveryProvider(DeliveryChannel.DESKTOP)
    service = _service(bus, collector)
    await service.start()

    seen: list[str] = []

    async def other_subscriber(event: SignalGenerated) -> None:
        seen.append(event.signal_id)

    await bus.subscribe(SignalGenerated, other_subscriber)
    try:
        # A signal with a non-string confidence would blow up the rule's
        # .lower(); the producer and the other subscriber must be unaffected.
        await bus.publish(
            SignalGenerated(
                signal_id="s9",
                instrument_key="AAPL",
                action="buy",
                direction="bullish",
                confidence="high",
                risk="low",
            )
        )
    finally:
        await service.stop()
    assert seen == ["s9"]
