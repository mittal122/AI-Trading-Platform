"""B2 — SMC signal scanner (§13).

Watchlist CRUD, settings clamp, candle-close gate (rescan skips same candle),
and signal lifecycle (accept -> paper trade, dismiss, guards). DB-backed (SQLite).
Run: PYTHONPATH=. .venv/bin/python tests/test_smc_scanner.py
"""

import backend.app.core.config  # noqa: F401

import asyncio

from backend.app.db.database import AsyncSessionLocal, create_tables
from backend.app.db.models import SmcSignal
from backend.app.db.repository.smc_repo import SmcScannerRepository
from backend.app.services.smc.scanner import scanner_service


async def _clear_watches():
    for w in await scanner_service.list_watches():
        await scanner_service.remove_watch(w.id)


async def main():
    await create_tables()
    await _clear_watches()

    # ----- watchlist CRUD -----
    w = await scanner_service.add_watch("BTCUSDT", "1h")
    watches = await scanner_service.list_watches()
    assert any(x.id == w.id and x.symbol == "BTCUSDT" for x in watches)
    assert await scanner_service.set_active(w.id, False)
    assert not next(x for x in await scanner_service.list_watches() if x.id == w.id).active
    # re-add upserts + reactivates
    w2 = await scanner_service.add_watch("BTCUSDT", "1h")
    assert w2.id == w.id and w2.active
    print("PASS watchlist CRUD: add / toggle / upsert-reactivate")

    # ----- settings clamp -----
    s = await scanner_service.update_settings(enabled=True, max_per_week=10)
    assert s.enabled and s.max_signals_per_week == 4, s   # clamped 2..4
    s = await scanner_service.update_settings(enabled=False, max_per_week=1)
    assert not s.enabled and s.max_signals_per_week == 2
    print(f"PASS settings clamp: 10->4, 1->2, enable toggles")

    # ----- candle-close gate -----
    r1 = await scanner_service.scan_once()
    r2 = await scanner_service.scan_once()   # same candle -> should skip the watch
    assert r1["scanned"] >= 1, r1
    assert r2["scanned"] == 0, f"rescan of same candle must skip: {r2}"
    print(f"PASS candle-close gate: scan1 scanned {r1['scanned']}, scan2 scanned {r2['scanned']}")

    # ----- signal lifecycle -----
    async with AsyncSessionLocal() as sess:
        repo = SmcScannerRepository(sess)
        sig = await repo.save_signal(SmcSignal(
            symbol="BTCUSDT", interval="1h", side="long",
            entry=100.0, stop_loss=95.0, take_profit_1=110.0, take_profit_2=115.0,
            score=80, reason_note="test", score_breakdown_json="[]",
            candle_time="t", status="new",
        ))
        sig2 = await repo.save_signal(SmcSignal(
            symbol="BTCUSDT", interval="4h", side="short",
            entry=100.0, stop_loss=105.0, take_profit_1=90.0, take_profit_2=85.0,
            score=75, reason_note="test", score_breakdown_json="[]",
            candle_time="t", status="new",
        ))
        sid, sid2 = sig.id, sig2.id

    accepted = await scanner_service.accept(sid, capital=1000, risk_pct=2)
    assert accepted.status == "accepted" and accepted.paired_trade_id is not None
    dismissed = await scanner_service.dismiss(sid2)
    assert dismissed.status == "dismissed"

    # guards: accepting an already-actioned signal fails
    try:
        await scanner_service.accept(sid, 1000, 2)
        raise AssertionError("expected ValueError on re-accept")
    except ValueError:
        pass
    print(f"PASS signal lifecycle: accept #{sid} -> paper trade #{accepted.paired_trade_id}, "
          f"dismiss #{sid2}, re-accept guarded")

    await _clear_watches()
    print("B2 OK")


if __name__ == "__main__":
    asyncio.run(main())
