# SMC Analyzer — Design Spec

**Date:** 2026-07-05
**Source:** `SMC_System_Documentation.pdf` (32 pages, "SMC Crypto Analyzer" — originally a Java/Spring Boot + React app).
**Goal:** Port the SMC (Smart Money Concepts) analysis engine into this Python/FastAPI + React platform as a **new self-contained section**, faithful to the document's exact rules and thresholds.

---

## Decisions (locked with user)

1. **Stack:** Port to our existing Python/FastAPI backend + React frontend. One stack, one deploy. Algorithms are language-agnostic — exact thresholds given in the doc, so the port is faithful.
2. **Build a FRESH `backend/app/services/smc/` module** — do NOT blend with the existing partial `pattern/smc_detector.py`. The doc's engine is far more rigorous (14-step pipeline, two scoring systems, verdict, trade plan) than the existing detector, which only finds structure.
3. **Scope:** Core engine first, then UI, then advanced chart. Three phases (A/B/C below).
4. **Frontend:** New "SMC Analyzer" page + its own sidebar entry, alongside the existing Dashboard/Retail/Backtest pages.
5. **Auth adaptation:** Doc's scanner/paper are per-user JWT. Our app is open-by-default (admin-token only on money actions). Phase A `/smc/analyze` is **public** (like `/patterns/scan`). Phase B scanner is **single-operator/global**, matching how our paper/live engines already work.

---

## Reused existing infrastructure (do not rebuild)

| Need | Reuse |
|---|---|
| Klines + pagination | `MarketService().get_market_data(symbol, interval, limit, end_time)` → df cols `timestamps,open,high,low,close,volume,amount` |
| Order book depth | `BinanceProvider.get_depth_summary(symbol, limit)` |
| Taker-buy flow | `BinanceProvider.get_buy_pressure(symbol, interval, limit)` (reads kline field 9) |
| ATR at any period | `IndicatorService.calculate_atr_at_period(df, period)` |
| Fractal swings | `services/pattern/swing_detector.py` `SwingDetector` |
| Chart zones (boxes) | `frontend/src/lib/rectanglePrimitive.ts` `RectanglesPrimitive` |
| Config pattern | class-with-attrs + module singleton (like `core/pattern_config.py`) |
| DB model/repo/service | `db/models.py` + `db/repository/*` + `services/db_service.py` (async SQLAlchemy 2.0) |
| Router registration | new `api/v1/smc.py` → import in `api/v1/router.py` → one `include_router` line |
| Frontend routing/nav | flat `<Route>` in `App.tsx`, one `LINKS` entry in `Sidebar.tsx`, axios fns in `api/client.ts` |

---

## Backend module layout (`backend/app/services/smc/`)

One file per pipeline concern (300–500 line cap, matches layer-separation rule: detectors detect, scorer scores, engine orchestrates):

| File | Doc § | Responsibility |
|---|---|---|
| `core/smc_config.py` | all | every threshold centralized (see "Key thresholds" below) |
| `swing.py` | §5.2 | fractal swing highs/lows (SWING_LENGTH=5, strictly-greater, ties disqualify → 5-bar confirm lag) |
| `structure.py` | §5.3 | HH/HL/LH/LL labels; BOS (with trend) / CHoCH (against, flips trend); series trend state |
| `order_blocks.py` | §5.4 | last opposite candle ≤15 bars before an up/down break; mitigation = **decisive close** through far side (wick ≠ mitigation), checked from 3 bars after |
| `fvg.py` | §5.5 | bull FVG `candle[i+1].low > candle[i-1].high`; fill from 2 bars after |
| `liquidity.py` | §5.6–5.7 | EQH/EQL pools (100-bar window, 0.3% tol); confirmed sweep = poke beyond + close back within 1–2 bars; recency (reversal ≤10 bars) for scoring; keep last 20 swings as stop refs |
| `dealing_range.py` | §5.1.6 | last 60 bars: rangeHi/Lo, EQ midpoint, pos=(close−lo)/range; premium/discount/equilibrium (0.45–0.55) |
| `volume.py` | §5 step7 | last-20 avg vs prior-40 avg (`ratio`); net up-vs-down volume (`trendVol` ∈ −1…1) |
| `poi.py` | §5.8–5.10 | POI = unmitigated OB ∩ open FVG same dir (overlap or gap ≤0.6×ATR); hasLiquidity if pool ≤0.5×ATR; de-dupe nested. Inducements (§5.9): HL(up)/LH(down) within 1.5×ATR of a deeper POI. Demand/supply zones (§5.10): base ≤3 candles range ≤0.6×ATR + ≥2.5×ATR impulse, ≥60% directional; mitigated by a single touch |
| `htf.py` | §5.12 | resample in-memory to HTF (1m→15, 5m→12, 15m→16, 1h→24, 4h→42, 1d→7); drop oldest partial; if ≥15 HTF bars run swing+structure → HTF trend |
| `scoring.py` | §6.1–6.2 | 6 market-bias components (Structure/OB/FVG/Liquidity/Zone/Volume), each −100…+100; weighted total → verdict label (BULLISH >+20 / BEARISH <−20 / NEUTRAL) + confidence |
| `confluence.py` | §6.3 | per-side checklist (8 factors → up to 110 pts) + 6 veto rules; side **fires** iff total ≥70 **and** no veto; strength label STRONG/MODERATE/WEAK/REJECTED |
| `trade_plan.py` | §7 | entry zone-priority (POI>OB>zone>swing>ATR fallback); structural stop (beyond zone + swing/EQL + 0.8×ATR buffer); min risk floor 1×ATR; TP1=2R, TP2=3.5R; TP1 liquidity-snap; R:R |
| `order_flow.py` | §8 | reuse depth + buy_pressure → `OrderFlow` (imbalance, CVD ratio, walls, pressure label). Live path only |
| `smc_engine.py` | §5.1 | orchestrate 14 steps → `AnalysisResult` (candles + all detections + scores + verdict + both-side plans + reasons + freeze stamp). Live overload takes order flow; backtest/scanner path omits it (walk-forward safe) |
| `backtest.py` | §9 | **Phase B** — walk-forward replay, realistic fills/stops/targets/time-exit, win rate/PF/drawdown/equity |
| `scanner.py` | §13 | **Phase B** — background watchlist scan (@scheduled 60s), signal creation rules, weekly cap |

Plus:
- `backend/app/schemas/smc.py` — all Pydantic DTOs.
- `backend/app/api/v1/smc.py` — router (`prefix="/smc"`).

---

## Key thresholds (from doc — go into `smc_config.py`)

- Swing: `SWING_LENGTH = 5` (strictly greater/less, ties disqualify).
- Order block: scan back `15` bars; mitigation from `3` bars after; decisive close only.
- FVG: 3-candle; fill from `2` bars after.
- Liquidity: window `100` bars; tolerance `0.3%` of window range (floor 1e-7); keep last `20` swings; sweep confirm within `1–2` bars; reversal recency `10` bars.
- Dealing range: `60` bars; equilibrium band `[0.45, 0.55]`.
- Volume: last-`20` avg vs prior-`40` avg; boost ×1.3 when recent >1.5× prior.
- POI: overlap or gap `≤0.6×ATR`; hasLiquidity `≤0.5×ATR`; inducement `≤1.5×ATR`.
- Demand/supply: base `≤3` candles, range `≤0.6×ATR`; impulse `≥2.5×ATR` over 5 candles, `≥60%` directional.
- ATR: `14`-period Wilder; fallback `max(2% of price, 0.0001)`.
- HTF bars-per-candle: `1m→15, 5m→12, 15m→16, 1h→24, 4h→42, 1d→7`; min `15` HTF bars.
- **Market-bias weights (§6.2):** `total = structure×0.30 + orderBlocks×0.20 + fvg×0.10 + liquidity×0.10 + zone×0.15 + volume×0.15`. Verdict: `>+20 BULLISH`, `<−20 BEARISH`, else NEUTRAL. `confidence = min(100, |total|×1.5)` → >65 high, >40 medium, else low.
- **Confluence checklist (§6.3, out of 110):** OB in zone +25 · FVG in zone +20 · HTF aligned +15 · correct dealing-range zone +15 · recent liquidity sweep +10 · POI present +10 · order-flow aligned +10 (live) · candle pattern +5. Zone-containment `containTol = 0.45×ATR`. **Fires iff total ≥70 AND no veto.**
- **Veto rules (§6.3):** (1) equilibrium 45–55% dead zone; (2) HTF/LTF disagreement; (3) counter-trend (long while LTF trend down / confirmed BOS never faded without opposing CHoCH); (4) zone vacuum (no same-dir POI/OB/FVG/zone within 2×ATR); (5) volatility out of band (ATR% <0.2% or >4%); (6) order-flow strongly against (live: long imbalance <−0.45 AND CVD <−0.25).
- **Trade plan (§7):** `maxDist = min(2×ATR, 3% of price)`; min risk floor `1×ATR`; `TP1=entry±2R`, `TP2=entry±3.5R`; structural stop scan swing/EQL from `2.5×ATR` below zone to `0.3×ATR` above, minus `0.8×ATR` buffer.
- **Order flow (§8):** depth band `max(1% of price, 2×ATR)`; walls ≥4× mean side volume, top-3; `imbalance=(bid−ask)/(bid+ask)`; `cvdRatio=delta/total`; pressure `>+0.12 buy / <−0.12 sell / else balanced`.

---

## Phasing (commit per feature, test each before next)

### Phase A — engine + minimal trustworthy UI
A1 scaffold (config, schemas, empty module, router stub) · A2 swing+structure · A3 order blocks+FVG · A4 liquidity+sweeps · A5 dealing range+volume · A6 ATR+HTF · A7 POI+inducements+demand/supply · A8 market-bias scoring+verdict · A9 confluence checklist+vetoes+firing · A10 trade plan · A11 order flow · A12 engine orchestration+reasons+freeze · A13 API endpoints+registration+live test · A14 frontend page (Verdict/TradePlan/Scores/ActiveZones/OrderFlow + lightweight-charts zones+levels) + sidebar + route + client · A15 reasons/explanation panel + polish.

### Phase B — backtester + scanner
B1 backtester (§9) + `/smc/backtest` + BacktestPanel UI · B2 signal scanner (§13): DB tables (watchlist/settings/signals), scheduled scan, signal endpoints, scanner UI (global/single-operator).

### Phase C — full chart
C1 the ~27 SMC overlay layers on the chart · C2 drawing tools, live freeze-bar drift, trade-from-chart.

---

## Testing

Each task ships a `tests/test_smc_*.py` (plain executable script, `PYTHONPATH=. .venv/bin/python tests/…`), verified against live Binance data + synthetic forced-branch data where the live market is quiet. Backend code changes require a manual uvicorn restart before live-testing (no `--reload`).

## Success criteria

Given a symbol/timeframe, `/smc/analyze` returns a faithful `AnalysisResult` whose verdict, both-side confluence scores, veto reasons, and trade plan (entry/SL/TP1/TP2/R:R) match the document's rules — and the SMC Analyzer page renders them clearly for a non-expert user, with the key SMC structures drawn on the chart.
