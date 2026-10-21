"""Hermetic-ish tests for QuotaLedger accounting (session mocked)."""

import asyncio
from datetime import date, timezone, datetime

import pytest

from ingestion import ingest_images as ii


class _FakeRow:
    def __init__(self, daily_cap):
        self.utc_date = date.today()
        self.daily_cap = daily_cap
        self.reserved = 0
        self.used = 0
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)


class _FakeSession:
    def __init__(self, row):
        self.row = row
        self._committed = False

    async def execute(self, stmt):
        class _R:
            def __init__(self, r):
                self._r = r
            def scalar_one_or_none(self):
                return self._r
        return _R(self.row)

    def add(self, obj):
        self.row = obj

    async def flush(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def begin(self):
        return self


@pytest.mark.asyncio
async def test_reserve_refuses_at_cap():
    ledger = ii.QuotaLedger(2)
    row = _FakeRow(2)
    sess = _FakeSession(row)
    # monkeypatch async_session
    import ingestion.ingest_images as m
    m.async_session = lambda: sess
    assert await ledger.reserve(sess) is True
    assert await ledger.reserve(sess) is True
    assert await ledger.reserve(sess) is False


@pytest.mark.asyncio
async def test_reconcile_moves_reserved_to_used():
    ledger = ii.QuotaLedger(2)
    row = _FakeRow(2)
    row.reserved = 1
    sess = _FakeSession(row)
    import ingestion.ingest_images as m
    m.async_session = lambda: sess
    await ledger.reconcile(sess, consumed=True)
    assert row.reserved == 0
    assert row.used == 1