# SMC Analyzer — Task Tracker

Living document. Update status as work proceeds. One commit per completed task.
Design spec: `docs/superpowers/specs/2026-07-05-smc-analyzer-design.md`.

Status key: `[ ]` todo · `[~]` in progress · `[x]` done (committed) · `[!]` blocked

---

## Phase A — Engine + minimal trustworthy UI

- [ ] **A1 — Scaffold.** `core/smc_config.py` (all thresholds), `schemas/smc.py` (DTOs), empty `services/smc/` package, `api/v1/smc.py` router stub registered in `router.py`. Boots clean.
- [ ] **A2 — Swing + market structure** (§5.2–5.3). Swings (reuse SwingDetector), HH/HL/LH/LL, BOS/CHoCH, trend state. `tests/test_smc_structure.py`.
- [ ] **A3 — Order blocks + FVG** (§5.4–5.5). OB detect + decisive-close mitigation; 3-candle FVG + fill. `tests/test_smc_ob_fvg.py`.
- [ ] **A4 — Liquidity pools + sweeps** (§5.6–5.7). EQH/EQL pools, confirmed sweeps, recency. `tests/test_smc_liquidity.py`.
- [ ] **A5 — Dealing range + volume** (§5.1.6, §5 step7). Premium/discount/EQ; volume ratio + trendVol. `tests/test_smc_range_volume.py`.
- [ ] **A6 — ATR + HTF trend** (§5.11–5.12). ATR(14) via IndicatorService; HTF resample + trend. `tests/test_smc_htf.py`.
- [ ] **A7 — POI + inducements + demand/supply** (§5.8–5.10). `tests/test_smc_poi.py`.
- [ ] **A8 — Market-bias scoring + verdict** (§6.1–6.2). 6 components, weighted total, verdict + confidence. `tests/test_smc_scoring.py`.
- [ ] **A9 — Confluence checklist + vetoes + firing** (§6.3). 8 factors + 6 vetoes, per-side fires ≥70. `tests/test_smc_confluence.py`.
- [ ] **A10 — Trade plan** (§7). Zone-priority entry, structural stop, TP1/TP2, R:R. `tests/test_smc_trade_plan.py`.
- [ ] **A11 — Order flow** (§8). depth+buy_pressure → OrderFlow. `tests/test_smc_order_flow.py`.
- [ ] **A12 — Engine orchestration** (§5.1). `smc_engine.analyze()` → full AnalysisResult + reasons + freeze stamp. `tests/test_smc_engine.py`.
- [ ] **A13 — API endpoints.** POST `/smc/analyze` + GET `/smc/analyze/{symbol}/{interval}`; live curl test through running server.
- [ ] **A14 — Frontend section.** `SmcAnalyzer.tsx` page, sidebar entry, route, `client.ts` fns; Verdict card · TradePlan card · 6 Score bars · ActiveZones · OrderFlow panel · lightweight-charts with OB/FVG zones + SL/TP/liquidity lines. `tsc` clean.
- [ ] **A15 — Reasons/explanation panel + polish.** "Why this signal" + veto reasons surfaced; simple UX pass for non-expert users.

## Phase B — Backtester + scanner

- [ ] **B1 — Backtester** (§9). `smc/backtest.py`, POST `/smc/backtest`, BacktestPanel UI (equity curve + stats).
- [ ] **B2 — Signal scanner** (§13). DB tables (watchlist/settings/signals), scheduled 60s scan, signal endpoints, scanner UI. Single-operator/global (auth adaptation).

## Phase C — Full chart

- [ ] **C1 — 27 SMC overlay layers** on the chart (order blocks, FVGs, BOS/CHoCH markers, liquidity lines, POI zones, demand/supply, sweep circles, inducement marks, EQ line, HTF banner, trend lines, plan levels, live-price tag).
- [ ] **C2 — Drawing tools, live freeze-bar drift, trade-from-chart.**

---

## Log

- 2026-07-05: Design approved. Recovered corrupted git repo (31 zero-byte loose objects → moved aside + `git fetch origin` repopulated from remote `9a6481e`). Spec + task doc created.
