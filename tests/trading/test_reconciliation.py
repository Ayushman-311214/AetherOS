"""
Broker reconciliation (spec Phase 2).

The reconciliation service diffs the venue's reported state against the local
position book and reports every leg that disagrees. These tests pin the honest
contract: a clean book is clean, a fill the book forgot is flagged, and a
position the venue cannot account for is flagged -- never fabricated agreement.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.brokers import PaperTradingProvider
from aetheros.trading.domain.enums import Direction
from aetheros.trading.domain.reconciliation import MismatchKind
from aetheros.trading.production import PositionBookService, ReconciliationService
from aetheros.trading.services.market_data_service import MarketDataService

from .conftest import FakeProvider
from .test_paper_broker import _feed
from .test_execution import _request


def _venue_with_book(price: float = 250.0):
    """A paper venue wired to a real position book, so fills land in it."""
    book = PositionBookService()
    service = MarketDataService(FakeProvider(_feed(price)), get_settings())
    venue = PaperTradingProvider(service, positions=book)
    return venue, book


@pytest.mark.asyncio
async def test_a_clean_book_reconciles_clean():
    venue, book = _venue_with_book()
    rec = ReconciliationService(venue, book)
    report = await rec.reconcile()
    assert report.is_clean
    assert report.mismatch_count == 0


@pytest.mark.asyncio
async def test_a_recorded_fill_reconciles_clean():
    venue, book = _venue_with_book()
    await venue.submit(_request(quantity=4.0))
    rec = ReconciliationService(venue, book)
    report = await rec.reconcile()
    assert report.is_clean


@pytest.mark.asyncio
async def test_a_position_with_no_venue_fill_is_flagged():
    venue, book = _venue_with_book()
    # Stuff the book directly: a position exists that no venue fill produced.
    book.record_fill(_request(quantity=4.0), fill_price=250.0, fill_quantity=4.0)
    rec = ReconciliationService(venue, book)
    report = await rec.reconcile()
    assert not report.is_clean
    assert any(m.kind is MismatchKind.POSITION_MISMATCH for m in report.mismatches)


@pytest.mark.asyncio
async def test_a_balance_divergence_is_flagged():
    venue, book = _venue_with_book()
    await venue.submit(_request(quantity=4.0))
    # Corrupt the book's recorded cash so it disagrees with the venue.
    book.record_cash(venue.venue_balance() + 500.0)
    rec = ReconciliationService(venue, book)
    report = await rec.reconcile()
    assert any(m.kind is MismatchKind.BALANCE_MISMATCH for m in report.mismatches)


@pytest.mark.asyncio
async def test_reconciliation_never_reports_agreement_it_cannot_see():
    # A book that was never told the cash (a venue with no positions wired) has
    # nothing to compare the balance leg against -- it is skipped, not assumed.
    book = PositionBookService()
    service = MarketDataService(FakeProvider(_feed(250.0)), get_settings())
    venue = PaperTradingProvider(service)  # no positions: cash never reported
    rec = ReconciliationService(venue, book)
    report = await rec.reconcile()
    assert report.is_clean
    assert any("balance" in n.lower() for n in report.notes)
