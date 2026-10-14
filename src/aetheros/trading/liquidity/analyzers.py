"""
Independent, deterministic liquidity analyzers.

Each analyzer is a pure function (or a tiny pure class) over the inputs it is
handed -- observations, an order book, a window of trade prints -- with no I/O,
no wall-clock reads and no hidden state, so the same historical input always
yields the same verdict (the backtestable-design requirement). They are kept
*separate* deliberately: imbalance, zones, sweeps, absorption, replenishment and
consumption are different questions, and collapsing them into one opaque score
is exactly the "largest order is important" shortcut the spec warns against.

Every score is documented, bounded and never a probability or a directional
call -- these describe liquidity *behaviour*, and interpretation belongs to the
feature/decision layers downstream.

The thresholds are named module constants, not inline magic numbers, so a reader
can see each one and change it in a single place.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.order_book import OrderBook
from .observation import LiquidityObservation
from .zone import LiquidityZone

# ----------------------------------------------------------------------
# Named thresholds (documented, single source of truth -- not magic numbers)
# ----------------------------------------------------------------------

#: A book level is "large" when it carries at least this multiple of the median
#: level size on its side. Chosen so ordinary noise levels don't form zones.
CLUSTER_SIZE_RATIO = 1.5

#: Two clusters merge into one zone when their price gap is at most this
#: fraction of the zone's own price span (keeps near levels as one wall).
ZONE_MERGE_GAP_RATIO = 0.25

#: Minimum share of the book's total resting liquidity a cluster must hold to
#: seed a zone at all (a level must matter, not just exist).
ZONE_MIN_SHARE = 0.05

#: |imbalance| at/above which the book is read as one-sided enough to flag.
IMBALANCE_FLAG = 0.20

#: A print consumes a resting zone when executed volume into it reaches at
#: least this fraction of the zone's displayed liquidity.
CONSUMPTION_RATIO = 0.5

#: Price must travel at least this fraction of the zone's height past its edge
#: to count the interaction as a *sweep* (cleared through) rather than a touch.
SWEEP_THROUGH_RATIO = 0.5

#: Absorption: net aggressive flow into a side with realised price movement
#: below this fraction of the window's typical bar range counts as absorbed.
ABSORPTION_PRICE_BAND = 0.5


# ----------------------------------------------------------------------
# 1. Order-book imbalance
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ImbalanceResult:
    """The resting-liquidity balance read off one observation."""

    bid_liquidity: float
    ask_liquidity: float
    imbalance: float          # -1..1, signed toward bid (positive) or ask
    dominant_side: str        # "bid" | "ask" | "balanced"
    strength: float           # 0..1 how lopsided (|imbalance| mapped)
    is_significant: bool      # |imbalance| cleared the flag threshold


def analyze_imbalance(observation: LiquidityObservation) -> ImbalanceResult:
    """
    Compare bid-side and ask-side resting liquidity on one observation.

    Returns the signed imbalance and whether it is lopsided enough to matter.
    A book with no displayed liquidity is ``balanced`` with zero strength --
    never a fabricated lean.
    """
    imbalance = observation.imbalance
    magnitude = abs(imbalance)
    dominant = "balanced"
    if imbalance >= IMBALANCE_FLAG:
        dominant = "bid"
    elif imbalance <= -IMBALANCE_FLAG:
        dominant = "ask"
    # Map |imbalance| to a 0..1 strength, saturating at 0.6 (a 60/20 or 80/20
    # book is about as one-sided as order books get before they just look empty).
    strength = min(1.0, magnitude / 0.6)
    return ImbalanceResult(
        bid_liquidity=observation.bid_liquidity,
        ask_liquidity=observation.ask_liquidity,
        imbalance=imbalance,
        dominant_side=dominant,
        strength=round(strength, 4),
        is_significant=magnitude >= IMBALANCE_FLAG,
    )


# ----------------------------------------------------------------------
# 2. Liquidity-zone detection
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Cluster:
    """One contiguous run of large resting levels on a book side."""

    side: str                      # "bid" | "ask"
    lower_price: float
    upper_price: float
    liquidity: float               # summed amount across the cluster
    level_count: int


def _cluster_levels(
    levels, side: str, total_liquidity: float
) -> list[Cluster]:
    """
    Group adjacent book levels that are individually large into clusters.

    A level qualifies when its amount is at least ``CLUSTER_SIZE_RATIO`` times
    the median level size on that side -- so the bar for "large" is set by the
    book itself, not a fixed quantity. Adjacent qualifying levels are merged
    into one cluster (one wall, not many zones); a gap of normal levels splits.
    """
    if not levels:
        return []
    sizes = sorted(level.amount for level in levels)
    n = len(sizes)
    # True median (mean of the two middle values for an even count), so a book
    # split between thin and fat levels has a median that separates them rather
    # than landing on the fat side and disqualifying the very wall we want.
    median = (
        sizes[n // 2]
        if n % 2 == 1
        else (sizes[n // 2 - 1] + sizes[n // 2]) / 2.0
    )
    threshold = median * CLUSTER_SIZE_RATIO

    clusters: list[Cluster] = []
    run: list = []
    for level in levels:
        if level.amount >= threshold and level.amount > 0:
            run.append(level)
        else:
            if run:
                clusters.append(_close_cluster(run, side))
                run = []
    if run:
        clusters.append(_close_cluster(run, side))

    # Keep only clusters that actually matter on this side of the book.
    return [
        c for c in clusters if total_liquidity > 0
        and c.liquidity / total_liquidity >= ZONE_MIN_SHARE
    ]


def _close_cluster(run, side: str) -> Cluster:
    prices = [level.price for level in run]
    return Cluster(
        side=side,
        lower_price=min(prices),
        upper_price=max(prices),
        liquidity=sum(level.amount for level in run),
        level_count=len(run),
    )


def _merge_clusters(clusters: list[Cluster]) -> list[Cluster]:
    """
    Merge clusters whose price bands come within ``ZONE_MERGE_GAP_RATIO`` of
    their span -- a wall split by a thin normal level is still one wall.
    """
    if not clusters:
        return []
    ordered = sorted(clusters, key=lambda c: c.lower_price)
    merged = [ordered[0]]
    for cluster in ordered[1:]:
        prev = merged[-1]
        span = max(prev.upper_price, cluster.upper_price) - min(
            prev.lower_price, cluster.lower_price
        )
        gap = cluster.lower_price - prev.upper_price
        if span > 0 and gap <= span * ZONE_MERGE_GAP_RATIO:
            merged[-1] = Cluster(
                side=prev.side,
                lower_price=min(prev.lower_price, cluster.lower_price),
                upper_price=max(prev.upper_price, cluster.upper_price),
                liquidity=prev.liquidity + cluster.liquidity,
                level_count=prev.level_count + cluster.level_count,
            )
        else:
            merged.append(cluster)
    return merged


def detect_zones(
    book: OrderBook, *, symbol: str | None = None
) -> tuple[Cluster, ...]:
    """
    Detect resting-liquidity clusters on a single order-book snapshot.

    Returns candidate ``Cluster`` bands (bid and ask). It is deliberately
    stateless: persistence, touches and sweeps are the tracker's job over the
    stream, not something a one-snapshot detector can honestly claim.
    """
    key = symbol or book.instrument.key
    _ = key  # zones are keyed by band + side; symbol rides on the tracker
    total_bid = sum(level.amount for level in book.bids)
    total_ask = sum(level.amount for level in book.asks)
    bid_clusters = _merge_clusters(_cluster_levels(book.bids, "bid", total_bid))
    ask_clusters = _merge_clusters(_cluster_levels(book.asks, "ask", total_ask))
    return tuple(bid_clusters + ask_clusters)


# ----------------------------------------------------------------------
# 3. Liquidity-sweep classification
# ----------------------------------------------------------------------

#: Honest sweep verdicts -- price consumed a zone, and what it did *after* is
#: observed separately. Neither is auto-classified as a reversal.
SWEEP_NONE = "none"
SWEEP_REJECTION = "rejection"    # entered the zone and closed back inside
SWEEP_ACCEPTANCE = "acceptance"  # cleared through the zone and held past it


@dataclass(frozen=True, slots=True)
class SweepResult:
    """What an interaction with a zone resolved to."""

    kind: str            # SWEEP_NONE / SWEEP_REJECTION / SWEEP_ACCEPTANCE
    direction: str       # "up" (swept asks) / "down" (swept bids) / "none"
    consumed: float      # executed volume that traded into/through the zone
    price_travelled: float  # how far past the zone edge price went
    detail: str


def classify_sweep(
    zone: LiquidityZone,
    *,
    intrazone_low: float,
    intrazone_high: float,
    close_price: float,
    consumed_volume: float,
) -> SweepResult:
    """
    Classify a price interaction with a zone.

    ``intrazone_low``/``intrazone_high`` are the price extremes reached while
    price was inside or beyond the zone; ``close_price`` is where it settled
    after the interaction; ``consumed_volume`` is the executed volume that
    traded into the zone. The verdict is honest about the two real outcomes:

    * **rejection** -- price entered the zone but settled back inside it (the
      resting liquidity held; the sweep was absorbed).
    * **acceptance** -- price cleared through the zone's far edge and *stayed*
      past it (the resting liquidity was consumed / the level gave way).

    An interaction that never meaningfully consumed the zone is ``none`` -- a
    graze is not a sweep, and a sweep is not auto-classified as a reversal.
    """
    if consumed_volume <= 0:
        return SweepResult(
            SWEEP_NONE, "none", consumed_volume, 0.0,
            "No executed volume into the zone.",
        )

    if zone.side == "ask":
        # Sweeping the asks means buying up through the supply wall.
        travelled = max(0.0, intrazone_high - zone.upper_price)
        through = travelled >= zone.height * SWEEP_THROUGH_RATIO
        accepted = through and close_price > zone.upper_price
        return SweepResult(
            kind=(
                SWEEP_ACCEPTANCE
                if accepted
                else (SWEEP_REJECTION if intrazone_high > zone.lower_price else SWEEP_NONE)
            ),
            direction="up",
            consumed=consumed_volume,
            price_travelled=travelled,
            detail=(
                "Cleared through the ask wall and held above it."
                if accepted
                else "Entered the ask wall and settled back inside it."
            ),
        )

    # Bid side: sweeping the bids means selling down through the demand wall.
    travelled = max(0.0, zone.lower_price - intrazone_low)
    through = travelled >= zone.height * SWEEP_THROUGH_RATIO
    accepted = through and close_price < zone.lower_price
    return SweepResult(
        kind=(
            SWEEP_ACCEPTANCE
            if accepted
            else (SWEEP_REJECTION if intrazone_low < zone.upper_price else SWEEP_NONE)
        ),
        direction="down",
        consumed=consumed_volume,
        price_travelled=travelled,
        detail=(
            "Cleared through the bid wall and held below it."
            if accepted
            else "Entered the bid wall and settled back inside it."
        ),
    )


# ----------------------------------------------------------------------
# 4. Absorption
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AbsorptionResult:
    """Whether aggressive flow was absorbed without proportional price move."""

    side: str            # "bid" (sell-side absorbed) / "ask" (buy-side) / "none"
    score: float         # 0..1 strength of the absorption read
    aggressive_volume: float
    price_move: float
    detail: str


def analyze_absorption(
    observation: LiquidityObservation,
    *,
    price_change: float,
    typical_price_move: float,
) -> AbsorptionResult:
    """
    Detect aggressive flow absorbed without a proportional price response.

    The spec's reading, stated as *evidence, not certainty*: heavy buyer-initiated
    printing with little upward movement suggests resting sellers absorbed the
    demand (sell-side absorption); heavy seller-initiated printing with little
    downward movement suggests resting buyers absorbed the supply (buy-side
    absorption).

    ``price_change`` is the realised price move over this observation's window
    (the caller supplies it, so absorption is judged against what price actually
    did, never guessed). ``typical_price_move`` is the window's reference move
    (e.g. a rolling ATR or median bar range) so the absorption bar is set by real
    volatility, not a fixed number.
    """
    buy = observation.executed_buy_volume
    sell = observation.executed_sell_volume
    move = abs(price_change)
    baseline = typical_price_move if typical_price_move > 0 else 0.0
    total = buy + sell
    if total <= 0 or baseline <= 0:
        return AbsorptionResult(
            "none", 0.0, total, move,
            "No executed flow or no volatility baseline to absorb against.",
        )

    # Movement ratio: how much price actually travelled vs the typical move.
    move_ratio = move / baseline
    quiet = move_ratio <= ABSORPTION_PRICE_BAND
    # Dominant aggressive side.
    if buy > sell and buy / total >= 0.6:
        # Aggressive buying, little upward move -> sellers absorbed (bid? no:
        # resting asks absorbed buys -> "ask" side absorbed).
        side = "ask"
        aggressor = "buy"
        flow_volume = buy
    elif sell > buy and sell / total >= 0.6:
        side = "bid"
        aggressor = "sell"
        flow_volume = sell
    else:
        return AbsorptionResult(
            "none", 0.0, total, move,
            "Executed flow is not one-sided enough to read absorption.",
        )

    if not quiet:
        return AbsorptionResult(
            "none", 0.0, total, move,
            f"Flow was {aggressor}-initiated but price moved with it "
            f"({move_ratio:.2f}x typical); not absorbed.",
        )

    # Strength = how dominant the flow was * how quiet price stayed.
    dominance = abs(buy - sell) / total
    quietness = 1.0 - move_ratio
    score = round(min(1.0, dominance * quietness), 4)
    return AbsorptionResult(
        side=side,
        score=score,
        aggressive_volume=flow_volume,
        price_move=move,
        detail=(
            f"{aggressor.capitalize()}-initiated flow ({flow_volume:.2f}) met "
            f"little price response ({move_ratio:.2f}x typical move) -> "
            f"{side}-side absorption."
        ),
    )


# ----------------------------------------------------------------------
# 5. Replenishment
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReplenishmentResult:
    """Whether resting liquidity at a zone kept reappearing after consumption."""

    replenishment_count: int
    score: float          # 0..1 how persistently it refilled
    detail: str


def analyze_replenishment(
    zone: LiquidityZone, *, consumed_volume: float, reappeared_volume: float
) -> ReplenishmentResult:
    """
    Score how strongly a zone's liquidity replenished after being consumed.

    ``consumed_volume`` is what the tape took from the zone; ``reappeared_volume``
    is resting liquidity that showed back up on the same band afterwards.
    Persistent refill suggests stronger, stickier interest -- evidence of a real
    wall, not a spoofed flash. Score scales with both the count and the refill
    ratio; it is evidence, never a guarantee the level holds.
    """
    if consumed_volume <= 0:
        return ReplenishmentResult(
            zone.replenishment_count, 0.0,
            "No consumption yet to replenish against.",
        )
    refill_ratio = min(1.0, reappeared_volume / consumed_volume)
    count_factor = min(1.0, zone.replenishment_count / 3.0)
    score = round(min(1.0, 0.5 * refill_ratio + 0.5 * count_factor), 4)
    return ReplenishmentResult(
        replenishment_count=zone.replenishment_count,
        score=score,
        detail=(
            f"Zone refilled {zone.replenishment_count}x with "
            f"{reappeared_volume:.2f} after {consumed_volume:.2f} was consumed."
        ),
    )


# ----------------------------------------------------------------------
# 6. Liquidity consumption
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConsumptionResult:
    """How much of a zone's resting liquidity the tape consumed."""

    consumed_volume: float
    consumption_ratio: float   # consumed / zone liquidity, 0..1
    fully_consumed: bool
    detail: str


def analyze_consumption(
    zone: LiquidityZone, *, executed_volume_into_zone: float, zone_liquidity: float
) -> ConsumptionResult:
    """
    Measure how much of a zone's resting liquidity the executed flow consumed.

    ``executed_volume_into_zone`` is the print volume that traded at/through the
    band; ``zone_liquidity`` is what the zone displayed. ``fully_consumed`` is an
    honest "the wall was eaten through" -- a partial eat is recorded as such.
    """
    if zone_liquidity <= 0:
        return ConsumptionResult(
            executed_volume_into_zone, 0.0, False,
            "Zone displayed no liquidity to consume.",
        )
    ratio = min(1.0, executed_volume_into_zone / zone_liquidity)
    fully = ratio >= CONSUMPTION_RATIO and executed_volume_into_zone >= zone_liquidity
    return ConsumptionResult(
        consumed_volume=executed_volume_into_zone,
        consumption_ratio=round(ratio, 4),
        fully_consumed=fully,
        detail=(
            f"Consumed {executed_volume_into_zone:.2f} of "
            f"{zone_liquidity:.2f} displayed liquidity "
            f"({ratio * 100:.0f}%)."
        ),
    )
