"""
Alert rules (spec Phase 23).

The *generation* half of the decoupling. A rule reads one trading event and
decides whether it warrants an alert, returning a finished :class:`Alert` or
``None``. Rules know about events and alerts; they know nothing about delivery
-- that is the router's and providers' job -- so the acceptance criterion
("trading events can generate alerts without coupling trading logic to a
notification provider") holds by construction.

Each rule covers one of the spec's alert kinds:

* **signal** -- a :class:`SignalGenerated` fired. Severity rises with the
  signal's own confidence.
* **news** -- a :class:`NewsSentimentAnalyzed` read came back directional with
  a reliable, non-mock source.
* **portfolio / risk** -- a :class:`RiskLimitReached` boundary was hit. Always
  CRITICAL: a breached risk limit is the one thing a desk must see.
* **pattern** -- a :class:`MarketEventsDetected` lookup found a high-impact
  event ahead (an event-risk pattern), or a :class:`MarketRegimeDetected`
  classified a decisive regime.

Price alerts in the spec's list are threshold watches a *caller* arms
("tell me if AAPL crosses 200"); the engine builds that alert directly from a
crossing via :func:`price_alert` rather than from an event, because no event
in this build carries a user-chosen threshold. The rule set here is the
event-driven half; the threshold half is a pure constructor the API layer
(Phase 24) will call.
"""

from __future__ import annotations

from ..events import (
    MarketEventsDetected,
    MarketRegimeDetected,
    NewsSentimentAnalyzed,
    RiskLimitReached,
    SignalGenerated,
)
from .domain import Alert, AlertKind, AlertSeverity, DeliveryChannel

# Confidence label -> alert severity for a generated signal.
_CONFIDENCE_SEVERITY = {
    "high": AlertSeverity.CRITICAL,
    "medium": AlertSeverity.WARNING,
    "low": AlertSeverity.INFO,
}


def signal_alert(
    event: SignalGenerated,
    *,
    channels: tuple[DeliveryChannel, ...] = (),
) -> Alert:
    """A SignalGenerated event -> a signal alert. Severity from its confidence."""
    severity = _CONFIDENCE_SEVERITY.get(
        event.confidence.lower(), AlertSeverity.INFO
    )
    return Alert(
        kind=AlertKind.SIGNAL,
        severity=severity,
        title=f"{event.action.upper()} signal: {event.instrument_key}",
        body=(
            f"A {event.direction} {event.action} signal was generated for "
            f"{event.instrument_key} (confidence {event.confidence or 'unknown'}, "
            f"risk {event.risk or 'unknown'})."
        ),
        instrument_key=event.instrument_key or None,
        channels=channels,
        source_event=event.name,
        data={
            "signal_id": event.signal_id,
            "action": event.action,
            "direction": event.direction,
            "confidence": event.confidence,
            "risk": event.risk,
        },
    )


def news_alert(
    event: NewsSentimentAnalyzed,
    *,
    channels: tuple[DeliveryChannel, ...] = (),
) -> Alert | None:
    """
    A directional, reliable news read -> a news alert.

    A neutral read, or one flagged unreliable or mock-sourced, raises nothing:
    the engine does not page a desk about non-news, and never about a synthetic
    number. ``is_reliable`` carries through so even a borderline alert stays
    honest about its basis.
    """
    direction = event.direction.lower()
    if direction not in ("bullish", "bearish"):
        return None
    if not event.is_reliable or event.source_tier == "mock":
        return None
    severity = (
        AlertSeverity.WARNING
        if abs(event.sentiment_score) >= 0.5
        else AlertSeverity.INFO
    )
    return Alert(
        kind=AlertKind.NEWS,
        severity=severity,
        title=f"{event.direction.capitalize()} news: {event.instrument_key}",
        body=(
            f"News sentiment for {event.instrument_key} read {event.direction} "
            f"(score {event.sentiment_score:+.2f}) across {event.item_count} "
            f"item(s): {event.positive_count} positive, {event.negative_count} "
            f"negative."
        ),
        instrument_key=event.instrument_key or None,
        channels=channels,
        source_event=event.name,
        is_reliable=event.is_reliable,
        data={
            "sentiment_score": event.sentiment_score,
            "item_count": event.item_count,
            "source_tier": event.source_tier,
        },
    )


def risk_alert(
    event: RiskLimitReached,
    *,
    channels: tuple[DeliveryChannel, ...] = (),
) -> Alert:
    """A RiskLimitReached event -> a CRITICAL portfolio alert, always."""
    return Alert(
        kind=AlertKind.PORTFOLIO,
        severity=AlertSeverity.CRITICAL,
        title=f"Risk limit reached: {event.limit_name}",
        body=(
            f"{event.limit_name} reached {event.observed_value:g} against a "
            f"limit of {event.limit_value:g}"
            + (
                f" on {event.instrument_key}"
                if event.instrument_key
                else ""
            )
            + (f". {event.reason}" if event.reason else ".")
        ),
        instrument_key=event.instrument_key,
        channels=channels,
        source_event=event.name,
        data={
            "limit_name": event.limit_name,
            "observed_value": event.observed_value,
            "limit_value": event.limit_value,
        },
    )


def event_risk_alert(
    event: MarketEventsDetected,
    *,
    channels: tuple[DeliveryChannel, ...] = (),
) -> Alert | None:
    """
    An upcoming high-impact calendar event -> a pattern alert.

    Only fires on a reliable, non-mock lookup that found a high-impact event;
    an empty or low-impact calendar, or an unreliable read, raises nothing.
    """
    if not event.has_high_impact:
        return None
    if not event.is_reliable or event.source_tier == "mock":
        return None
    when = (
        f" in ~{event.next_event_days:.1f} day(s)"
        if event.next_event_days is not None
        else ""
    )
    label = event.next_high_impact_kind or event.next_event_type or "event"
    return Alert(
        kind=AlertKind.PATTERN,
        severity=AlertSeverity.WARNING,
        title=f"Event risk ahead: {event.instrument_key}",
        body=(
            f"A high-impact {label} is scheduled for {event.instrument_key}"
            f"{when}. Model reliability around scheduled events is reduced."
        ),
        instrument_key=event.instrument_key or None,
        channels=channels,
        source_event=event.name,
        is_reliable=event.is_reliable,
        data={
            "next_event_type": event.next_event_type,
            "next_high_impact_kind": event.next_high_impact_kind,
            "next_event_days": event.next_event_days,
        },
    )


def regime_alert(
    event: MarketRegimeDetected,
    *,
    channels: tuple[DeliveryChannel, ...] = (),
) -> Alert | None:
    """
    A decisive regime classification -> a pattern alert.

    Only a trending regime on a reliable, non-mock read raises an alert; a
    neutral/ranging regime, or an unreliable one, is not news a desk is paged
    about.
    """
    regime = event.regime.lower()
    if "trend" not in regime:
        return None
    if not event.is_reliable or event.source_tier == "mock":
        return None
    return Alert(
        kind=AlertKind.PATTERN,
        severity=AlertSeverity.INFO,
        title=f"Regime: {event.regime} on {event.instrument_key}",
        body=(
            f"{event.instrument_key} classified {event.regime} on "
            f"{event.timeframe or 'its timeframe'}"
            + (f" (ADX {event.adx:.1f})" if event.adx is not None else "")
            + "."
        ),
        instrument_key=event.instrument_key or None,
        channels=channels,
        source_event=event.name,
        is_reliable=event.is_reliable,
        data={"regime": event.regime, "adx": event.adx},
    )


def price_alert(
    *,
    instrument_key: str,
    price: float,
    threshold: float,
    direction: str,
    channels: tuple[DeliveryChannel, ...] = (),
) -> Alert:
    """
    A caller-armed price threshold was crossed -> a price alert.

    Built directly from a crossing (not an event) because no event in this
    build carries a user-chosen threshold. ``direction`` is "above" or "below"
    -- the side of the threshold ``price`` landed on.
    """
    return Alert(
        kind=AlertKind.PRICE,
        severity=AlertSeverity.WARNING,
        title=f"{instrument_key} {direction} {threshold:g}",
        body=(
            f"{instrument_key} traded at {price:g}, {direction} the watched "
            f"threshold of {threshold:g}."
        ),
        instrument_key=instrument_key,
        channels=channels,
        source_event="price_watch",
        data={"price": price, "threshold": threshold, "direction": direction},
    )
