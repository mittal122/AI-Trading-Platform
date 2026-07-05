# SMC Analyzer — Task Tracker

Living document. Update status as work proceeds. One commit per completed task.
Design spec: `docs/superpowers/specs/2026-07-05-smc-analyzer-design.md`.

Status key: `[ ]` todo · `[~]` in progress · `[x]` done (committed) · `[!]` blocked

---

## Phase A — Engine + minimal trustworthy UI

- [x] **A1 — Scaffold.** `core/smc_config.py` (all thresholds), `schemas/smc.py` (DTOs), empty `services/smc/` package, `api/v1/smc.py` router stub registered in `router.py`. Boots clean. *(weights sum 1.0, router `/smc` registered)*
- [x] **A2 — Swing + market structure** (§5.2–5.3). Swings (reuse SwingDetector), HH/HL/LH/LL, BOS/CHoCH, trend state. `tests/test_smc_structure.py`. *(synthetic exact seq CHoCH→BOS→CHoCH→BOS; live 38 swings/17 events)*
- [x] **A3 — Order blocks + FVG** (§5.4–5.5). OB detect + decisive-close mitigation; 3-candle FVG + fill. `tests/test_smc_ob_fvg.py`. *(wick≠mitigation verified; live 17 OBs/59 FVGs)*
- [x] **A4 — Liquidity pools + sweeps** (§5.6–5.7). EQH/EQL pools, confirmed sweeps, recency. `tests/test_smc_liquidity.py`. *(synthetic sweep+bare-poke+recency verified; live pools legitimately rare on trending data — 0.3%-of-range tol, forms in ranges)*
- [x] **A5 — Dealing range + volume** (§5.1.6, §5 step7). Premium/discount/EQ; volume ratio + trendVol. `tests/test_smc_range_volume.py`. *(pos→zone exact; trendVol ±1/spike; live sane)*
- [x] **A6 — ATR + HTF trend** (§5.11–5.12). ATR(14) direct (simple mean of Wilder TR, not RMA); HTF in-memory resample + trend. `tests/test_smc_htf.py`. *(ATR/resample exact, synthetic HTF uptrend, gating, live consistent)*
- [x] **A7 — POI + inducements + demand/supply** (§5.8–5.10). `tests/test_smc_poi.py`. *(intersection/union/dedup/liquidity, inducement gating, demand touch-mitigation; live 4 POIs/9 ind/3 zones)*
- [x] **A8 — Market-bias scoring + verdict** (§6.1–6.2). 6 components, weighted total, verdict + confidence. `tests/test_smc_scoring.py`. *(each component exact; formula 56.5→BULLISH/84.75; boundaries; live BULLISH)*
- [x] **A9 — Confluence checklist + vetoes + firing** (§6.3). 8 factors + 6 vetoes, per-side fires ≥70. `tests/test_smc_confluence.py`. *(full-fire 110/STRONG, all 6 vetoes isolated, strength bands; live fires nothing — rare by design)*
- [x] **A10 — Trade plan** (§7). Zone-priority entry, structural stop, TP1/TP2, R:R. `tests/test_smc_trade_plan.py`. *(POI-priority, structural stop, TP1 liq-snap 2.4RR, risk floor, ATR fallback, short mirror; live both sides valid)*
- [x] **A11 — Order flow** (§8). raw depth (band+walls) + aggTrades CVD → OrderFlow. `tests/test_smc_order_flow.py`. *(band/imbalance/walls/CVD exact, non-fatal trades, live fetch works)*
- [x] **A12 — Engine orchestration** (§5.1). `smc_engine.analyze()` → full AnalysisResult + reasons + freeze stamp + annotations. `tests/test_smc_engine.py`. *(~25ms full pipeline, invariants across 3 symbols, OF attach, walk-forward safe)*
- [x] **A13 — API endpoints.** POST `/smc/analyze` + GET `/smc/analyze/{symbol}/{interval}`; live curl test through running server. *(live server verified: POST/GET full result, 400 bad interval, 422 limit; `tests/test_smc_endpoint.py`)*
- [x] **A14 — Frontend section.** `SmcAnalyzer.tsx` page, sidebar entry, route, `client.ts` fns; Verdict card · both TradePlan cards · 6 Score bars · OrderFlow panel · signal banner · lightweight-charts with OB/FVG/POI zones + BOS/CHoCH markers + plan levels. `tsc` clean. *(verified in headless Chrome: renders, 0 console errors, zones/markers drawn, matches design system)*
- [x] **A15 — Reasons/explanation panel + polish.** "Why this read" reasons + veto reasons surfaced; plain-language factor labels; live-structure counts strip; bias-vs-signal explainer; risk disclaimer. *(verified in browser)*

## Phase B — Backtester + scanner

- [x] **B1 — Backtester** (§9). `smc/backtest.py`, POST `/smc/backtest`, BacktestPanel UI (SVG equity curve + stats + trades table). `tests/test_smc_backtest.py`. *(metrics exact, walk-forward ~2-3s, deterministic; live curl 200; browser-verified panel)*
- [x] **B2 — Signal scanner** (§13). DB tables (watchlist/settings/signals, single-operator/global), 60s asyncio scheduler, candle-close gate, weekly cap + 24h dedup, accept→paper-trade / dismiss, 11 endpoints, scanner UI panel. `tests/test_smc_scanner.py`. *(CRUD/clamp/gate/lifecycle tested; live curl + browser verified; accept opened paper #1)*
      NOTE: new tables auto-created via `create_tables()` (dev/SQLite). For prod Postgres, autogenerate an Alembic migration for `smc_watchlist`/`smc_scanner_settings`/`smc_signals`.

## Phase C — Full chart

- [x] **C1 — SMC overlay layers + toggle bar** on the chart. Zones (OB/FVG/POI/demand-supply), BOS/CHoCH markers, HH/HL/LH/LL swing labels, dashed EQH/EQL liquidity lines, equilibrium line, sweep markers, inducement marks, HTF trend banner, plan levels — each individually toggleable (persisted). *(browser-verified: toggling Swings drew all labels; 0 console errors)*
- [x] **C2 — Live freeze-bar drift + trade-from-chart.** FreezeBar (frozen vs live price polled every 5s, drift %, plan-level-cross warning, Re-analyze). One-click "Paper-trade this plan" on each plan card → opens a paper order via ManualPaperTrader. *(browser-verified: live drift updates, paper order #1 opened)*
      DEFERRED (disclosed): freehand drawing tools (pen/trendline/rectangle/eraser) — heavy, low value for an auto-drawing SMC chart; the analysis zones/levels are drawn automatically already.

---

## Log

- 2026-07-05: Design approved. Recovered corrupted git repo (31 zero-byte loose objects → moved aside + `git fetch origin` repopulated from remote `9a6481e`). Spec + task doc created.
- 2026-07-05: **Phase C COMPLETE (C1–C2).** Chart overlay layers + toggle bar (swings/sweeps/inducements/EQ/liquidity/HTF banner) + freeze-bar live drift + one-click paper-trade-this-plan. Freehand drawing tools deferred (disclosed). **All 3 phases (A/B/C) of the SMC Analyzer now shipped.**
- 2026-07-05: **Phase B COMPLETE (B1–B2).** Backtester (§9, walk-forward, BacktestPanel) + signal scanner (§13, 60s scheduler, watchlist/settings/signals, accept→paper-trade). All tested + live-verified. **Next: Phase C (full 27-layer chart + drawing tools).**
- 2026-07-05: **Phase A COMPLETE (A1–A15).** Full SMC engine ported to Python/FastAPI (12 service modules, all unit+live tested), `/smc/analyze` endpoint live-verified through the running Kronos-loaded server, and the SMC Analyzer frontend section (page + sidebar + chart with drawn zones/markers + verdict/plan/scores/order-flow cards) verified in headless Chrome with zero console errors. All 12 `test_smc_*.py` pass; existing tests unaffected. One commit per task, all pushed. **Next: Phase B (backtester §9 + signal scanner §13), then Phase C (full 27-layer chart).**
