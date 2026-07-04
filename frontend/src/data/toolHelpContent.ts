export interface ToolHelpContent {
  key: string
  name: string
  whatIsIt: string
  whyTradersUseIt: string
  whatItDetects: string
  whyItMatters: string
  calculationMethod: string
  detectionLogic: string
  aiInvolvement: string
  mathConcepts: string
  whenToEnable: string
  howToInterpret: string
  howToConfirm: string
  commonMistakes: string[]
  bestPractices: string[]
  recommendedTimeframe: string
  recommendedConditions: string
  realExample: string
  institutionalUse: string
  whenItFails: string
  whenToAvoid: string
  combineWith: string
}

export const TOOL_HELP: Record<string, ToolHelpContent> = {
  support_resistance: {
    key: 'support_resistance',
    name: 'Support & Resistance',
    whatIsIt: 'Price levels where the market has repeatedly reversed or paused — support is where buyers have historically stepped in, resistance is where sellers have historically capped price.',
    whyTradersUseIt: 'They mark where the crowd\'s memory of past price action creates real supply/demand imbalances — orders cluster at these levels, making them self-reinforcing.',
    whatItDetects: 'Swing highs/lows that cluster near the same price (multiple touches), plus psychological round-number levels near the current price.',
    whyItMatters: 'Most technical setups (breakouts, bounces, stop placement) are defined relative to these levels — they are the skeleton the rest of technical analysis hangs on.',
    calculationMethod: 'Detects fractal swing points (local highs/lows), clusters ones within a tight price tolerance into a single level, and counts touches. Round numbers near the current price (e.g. $61,000/$61,500) are added separately as psychological levels.',
    detectionLogic: 'A level needs at least 2 touches within tolerance to count — a single swing point is just noise, not a level.',
    aiInvolvement: 'None in detection (pure geometry). AI is only used, on-demand, to reason about confluence with other enabled tools.',
    mathConcepts: 'Local extrema detection (fractals) + tolerance-based clustering (nearest-neighbor grouping by percentage distance).',
    whenToEnable: 'Always-on baseline for most strategies — it\'s the reference grid everything else is read against.',
    howToInterpret: 'More touches = more significant. A level tested 4+ times and still holding is stronger than one touched twice. Levels get weaker each time they\'re tested (liquidity behind them gets consumed).',
    howToConfirm: 'Look for a reaction at the level — a rejection wick, a volume spike, or a slowdown in momentum — before assuming it will hold. A level alone is not a signal.',
    commonMistakes: [
      'Treating a level as an exact price instead of a zone — price rarely reverses at the exact number.',
      'Assuming every level holds — the more times a level is tested, the more likely it eventually breaks.',
      'Ignoring higher-timeframe levels while trading a lower timeframe.',
    ],
    bestPractices: [
      'Weight higher-timeframe levels more heavily than lower-timeframe ones.',
      'Use levels as a zone (± a bit of ATR), not a single price.',
      'Combine with volume — a breakout through a level on high volume is more credible than on low volume.',
    ],
    recommendedTimeframe: 'Works on any timeframe; higher timeframes (4h/1d) give more reliable, longer-lasting levels.',
    recommendedConditions: 'Ranging or consolidating markets, where price is bouncing between defined boundaries.',
    realExample: 'If price approaches a resistance level that has rejected price twice before, and a bearish rejection candle forms with rising volume, that is a higher-probability short setup than a blind short at any random price.',
    institutionalUse: 'Institutions place large resting orders around known levels (both to enter and to defend positions), which is precisely what makes these levels self-fulfilling — the level exists because big players act on it.',
    whenItFails: 'In strong trending or high-volatility news-driven moves, price can blow through multiple levels without pausing — S/R works best in orderly markets, not during momentum spikes.',
    whenToAvoid: 'Avoid trading a level in isolation right before major scheduled news/events, when volatility can override the level entirely.',
    combineWith: 'Volume, Moving Averages (a level near a major MA is stronger), and Market Structure (a level that also marks the last swing point in a BOS/CHOCH is more significant).',
  },

  moving_averages: {
    key: 'moving_averages',
    name: 'Moving Averages',
    whatIsIt: 'A smoothed line of average price over N periods (EMA weights recent price more, SMA weights all periods equally, WMA linearly weights toward recent).',
    whyTradersUseIt: 'To filter out noise and see the underlying trend direction and speed without reacting to every individual candle.',
    whatItDetects: 'Trend direction/strength (via the EMA stack ordering), and crossover events — specifically Golden Cross (SMA50 crosses above SMA200, classic long-term bullish signal) and Death Cross (the bearish mirror).',
    whyItMatters: 'Moving averages are the single most widely-used trend filter in trading — most systematic and discretionary traders reference at least one.',
    calculationMethod: 'EMA weights recent candles exponentially higher; SMA is a plain rolling average; WMA weights linearly by recency. Computed at 20/50/100/200 periods.',
    detectionLogic: 'Golden/Death Cross checked via the prior bar vs. current bar relationship between SMA50 and SMA200 — a cross only fires on the exact bar it happens, not every bar after.',
    aiInvolvement: 'None in detection. AI (on-demand) can reason about how the MA trend agrees or disagrees with other enabled tools.',
    mathConcepts: 'Exponential weighting (EMA), simple arithmetic mean (SMA), linear weighting (WMA).',
    whenToEnable: 'Nearly always — it is a baseline trend filter for almost every strategy.',
    howToInterpret: 'Price above a rising MA = bullish bias; below a falling MA = bearish. A "stacked" order (20 > 50 > 200, all rising) is a strong trend; a tangled/crossed stack means a choppy, directionless market.',
    howToConfirm: 'Don\'t trade the cross itself — wait for price to hold above/below the crossed averages for a candle or two, since crosses can whipsaw in choppy markets.',
    commonMistakes: [
      'Using a Golden/Death Cross as a standalone entry signal — it is a lagging, long-term regime signal, not a precision entry tool.',
      'Ignoring how far apart the MAs are — a cross with MAs nearly flat/close together is much weaker than one with a clear separating trend.',
      'Applying short-period MAs (e.g. 20) on very low timeframes where noise dominates the signal.',
    ],
    bestPractices: [
      'Use faster MAs (20/50) for entries/exits, slower MAs (100/200) for overall regime/bias.',
      'Treat a Golden/Death Cross as a multi-week regime signal, not a trade trigger.',
      'Watch for price using a rising MA as dynamic support (or a falling MA as dynamic resistance).',
    ],
    recommendedTimeframe: 'Golden/Death Cross is most meaningful on daily+ charts; shorter MAs work fine intraday.',
    recommendedConditions: 'Trending markets — moving averages lag and whipsaw badly in tight ranges.',
    realExample: 'If SMA50 crosses above SMA200 (Golden Cross) on the daily chart while price also holds above VWAP and a key resistance-turned-support level, that\'s multiple independent tools agreeing on a bullish regime shift, not just one lagging signal in isolation.',
    institutionalUse: 'Large systematic/trend-following funds use long-period MA crossovers as core regime filters for position sizing and allocation — this is one of the oldest institutional CTA-style strategies.',
    whenItFails: 'In sideways/choppy markets, price whipsaws across MAs repeatedly, generating false crosses with no follow-through.',
    whenToAvoid: 'Avoid relying on MAs alone in low-volatility consolidation — combine with ATR/volatility context first.',
    combineWith: 'VWAP (institutional fair value), ATR (position sizing/stop distance), and Market Structure (does the MA trend match the actual swing structure?).',
  },

  vwap: {
    key: 'vwap',
    name: 'VWAP',
    whatIsIt: 'Volume-Weighted Average Price — the average price paid for an asset over a period, weighted by how much volume traded at each price. Considered the "fair value" institutions benchmark execution against.',
    whyTradersUseIt: 'Institutions use VWAP to judge whether their own execution was good or bad, and to gauge whether the current price is cheap or expensive relative to where most volume actually traded.',
    whatItDetects: 'Whether current price is trading above (bullish) or below (bearish) the volume-weighted fair value, plus standard-deviation bands showing statistically extended price.',
    whyItMatters: 'A large share of institutional order flow is explicitly benchmarked to VWAP — it is one of the few levels genuinely "watched" by large size, not just retail pattern-recognition.',
    calculationMethod: 'Cumulative sum of (typical price × volume) divided by cumulative volume, starting from an anchor point. Daily VWAP anchors at the start of the current UTC day; Anchored VWAP auto-anchors at the most recent significant swing point. Bands are volume-weighted standard deviation around the VWAP line.',
    detectionLogic: 'Bias = price above or below the daily VWAP line at the current bar.',
    aiInvolvement: 'None in detection. AI (on-demand) can reason about VWAP vs. other tools\' bias.',
    mathConcepts: 'Weighted average, cumulative sum, weighted standard deviation.',
    whenToEnable: 'Especially useful on lower/intraday timeframes where session-based fair value matters most.',
    howToInterpret: 'Price above VWAP = buyers in control this session; below = sellers in control. The further price stretches from VWAP (especially beyond the 2-stddev band), the more "extended" and mean-reversion-prone it becomes.',
    howToConfirm: 'A bounce off VWAP with a rejection candle, or a clean reclaim after being below it, is a stronger signal than price randomly touching the line.',
    commonMistakes: [
      'Treating VWAP as a static support/resistance level — it moves every candle, it is not a fixed line.',
      'Using session VWAP on assets/markets that trade 24/7 without a clear "session" (crypto) without being explicit about the anchor.',
      'Ignoring that VWAP resets — comparing today\'s VWAP position to yesterday\'s is meaningless.',
    ],
    bestPractices: [
      'Use the 1-2 stddev bands as a stretch/mean-reversion gauge, not just the line itself.',
      'Combine daily VWAP (session fair value) with anchored VWAP (fair value since the last major swing) for a fuller picture.',
      'Fade extreme band touches only when there is also a S/R or pattern confluence — never blindly.',
    ],
    recommendedTimeframe: '1m–1h for the daily anchor to still be meaningful (on daily+ charts the "day" anchor loses relevance).',
    recommendedConditions: 'Works in both trending and ranging conditions, but is most actionable on liquid, high-volume symbols.',
    realExample: 'If price stretches to the +2 standard-deviation band above VWAP on declining volume, that is a classic "overextended, mean-reversion likely" signal institutions watch for before fading a move.',
    institutionalUse: 'VWAP is the literal execution benchmark for algorithmic institutional order slicing (VWAP execution algorithms exist specifically to match this line) — it is not just a chart indicator, it is operational infrastructure for big players.',
    whenItFails: 'On low-volume/illiquid symbols the volume weighting becomes noisy and less meaningful. It can also mean very little on a symbol with no clear "session" structure.',
    whenToAvoid: 'Avoid over-anchoring to session VWAP on assets that trade continuously with no natural daily reset in participant behavior.',
    combineWith: 'Support & Resistance (VWAP band touches near a known level are stronger), ATR (band width context), and Volume tools.',
  },

  pivot_points: {
    key: 'pivot_points',
    name: 'Pivot Points',
    whatIsIt: 'A set of levels computed from the prior period\'s high/low/close, projecting likely support/resistance for the current period. Five variants exist (Classic, Fibonacci, Camarilla, Woodie, DeMark), each with a different formula philosophy.',
    whyTradersUseIt: 'They are deterministic, calculated fresh every period, and widely watched — especially by day traders and floor-trading-derived strategies — making them somewhat self-fulfilling.',
    whatItDetects: 'A full ladder of support/resistance levels (R1-R3/S1-S3 depending on system) derived purely from the prior day\'s range, plus whether current price sits above or below the central pivot.',
    whyItMatters: 'Unlike swing-based S/R, pivots update automatically and objectively every period with no subjective level-drawing — useful as an unbiased reference grid.',
    calculationMethod: 'Classic: PP=(H+L+C)/3, R1/S1/R2/S2/R3/S3 derived from PP and the prior range. Fibonacci: same PP, offsets scaled by 0.382/0.618/1.0 of the range. Camarilla: tight levels close to the prior close (1.1/12, 1.1/6, 1.1/4, 1.1/2 multipliers) — designed for reversal trades. Woodie: PP weights the close double. DeMark: PP formula depends on whether the prior close was above or below the prior open.',
    detectionLogic: 'Always computed from the prior FULL DAILY period\'s O/H/L/C, regardless of your chart\'s own timeframe — this is the standard professional convention (daily pivots shown on any intraday chart).',
    aiInvolvement: 'None in detection. AI (on-demand) can reason about pivot bias vs. other tools.',
    mathConcepts: 'Weighted averages and range-proportional offsets; DeMark uses conditional logic based on candle direction.',
    whenToEnable: 'Best for intraday trading where "today vs. yesterday\'s range" framing is directly actionable.',
    howToInterpret: 'Price above the central pivot (PP) = bullish bias for the period; below = bearish. R1/S1 are the first, most-likely-to-be-tested targets; R3/S3 are extreme, low-probability targets.',
    howToConfirm: 'Camarilla levels are specifically designed as reversal zones (fade R3/S3, breakout past R4/S4) — treat other systems\' outer levels more as targets than entry triggers.',
    commonMistakes: [
      'Using pivot levels from a wildly different volatility regime than the prior day without adjusting expectations.',
      'Treating all 5 systems as interchangeable — Camarilla is built for mean-reversion, others for directional projection.',
      'Ignoring that pivots reset daily — yesterday\'s pivots are stale after the new day begins.',
    ],
    bestPractices: [
      'Use Classic/Fibonacci for directional bias and targets; use Camarilla specifically for intraday reversal/fade setups.',
      'Treat R1/S1 as the most reliable, most-often-reached levels; R2/R3 as increasingly unlikely.',
      'Check where price opened relative to PP — opening above PP already tilts the day bullish, and vice versa.',
    ],
    recommendedTimeframe: '5m–1h for the daily pivot ladder to be actionable within a single trading day.',
    recommendedConditions: 'Most useful in liquid markets with a meaningful "daily range" concept.',
    realExample: 'A price that opens below the Classic PP, tests S1, and then reclaims PP with strength is a well-known intraday "failed breakdown, reversal to bullish" pattern many day traders specifically watch for.',
    institutionalUse: 'Pivot points originated from floor-trading conventions and remain heavily used by day-trading desks as a quick, no-subjectivity reference grid for the session.',
    whenItFails: 'On days with major news/gaps, price can blow straight through R3/S3 without any reaction — pivots assume a "normal" range day.',
    whenToAvoid: 'Avoid Camarilla-style fade trades directly ahead of high-impact scheduled news.',
    combineWith: 'ATR (is today\'s expected range even large enough to reach R2/R3?), Support & Resistance (do pivot levels line up with swing-based levels?).',
  },

  atr: {
    key: 'atr',
    name: 'Average True Range',
    whatIsIt: 'A volatility measure — the average size of a candle\'s true range (accounting for gaps) over N periods. It measures HOW MUCH price is moving, not which direction.',
    whyTradersUseIt: 'To size stops/targets and position sizes proportionally to actual current volatility, instead of using fixed dollar/percent amounts that don\'t adapt to changing conditions.',
    whatItDetects: 'Current volatility level, classified Low/Medium/High relative to price, plus ATR-scaled suggested stop-loss and take-profit levels for both long and short scenarios.',
    whyItMatters: 'Using volatility-adjusted stops means you get out of a bad trade at a consistent conviction level regardless of how choppy or calm the market currently is — a fixed-dollar stop makes no sense in both a quiet market and a volatile one.',
    calculationMethod: 'True Range = max(high-low, |high-prev_close|, |low-prev_close|); ATR is the rolling average of True Range over 14 periods. Volatility classification compares ATR as a % of price against configured thresholds.',
    detectionLogic: 'Not pattern detection — a continuous volatility measurement, always available regardless of market condition.',
    aiInvolvement: 'None in detection. AI (on-demand) can factor ATR-based volatility into confluence reasoning with other tools.',
    mathConcepts: 'Rolling average, true range (gap-aware range calculation).',
    whenToEnable: 'Always-on — it underlies proper risk management for essentially every other tool\'s suggested stop/target.',
    howToInterpret: 'HIGH volatility = wider stops needed, smaller position size for the same dollar risk. LOW volatility = tighter stops possible, but also lower reward potential per trade — and low volatility often precedes an expansion move.',
    howToConfirm: 'Don\'t act on ATR alone — it tells you HOW to size a trade, not WHETHER to take one. Combine with a directional signal from another tool.',
    commonMistakes: [
      'Using a fixed stop-loss percentage across all market conditions instead of scaling with ATR.',
      'Confusing "low volatility" with "safe" — low-ATR consolidation frequently precedes a violent breakout.',
      'Ignoring that ATR itself lags — it describes recent past volatility, not necessarily what\'s about to happen.',
    ],
    bestPractices: [
      'Size stops at 1.5-2x ATR to avoid getting stopped out by normal noise.',
      'Size position size inversely to ATR — bigger ATR, smaller position, for consistent dollar risk.',
      'Watch for ATR expanding from a low base — that\'s often the start of a real directional move.',
    ],
    recommendedTimeframe: 'Any — but the ATR period should roughly match your holding period (intraday traders often use a shorter ATR).',
    recommendedConditions: 'Always relevant; especially critical before entering during a volatility regime change.',
    realExample: 'If ATR has been compressing for days (a "squeeze") and then suddenly expands alongside a breakout above resistance, that combination — volatility expansion + structural breakout — is a much higher-conviction signal than the breakout alone.',
    institutionalUse: 'ATR-based position sizing is standard practice in professional risk management — many systematic funds size every position so that 1 ATR of adverse movement equals a fixed, small percentage of portfolio risk.',
    whenItFails: 'ATR says nothing about direction — a rising ATR can accompany either a strong trend or a violent chop, so used alone it can mislead about market character.',
    whenToAvoid: 'Don\'t use ATR-based stops as your ONLY exit logic in a strongly trending market — pure ATR trailing can exit trend trades too early.',
    combineWith: 'Every directional tool (S/R, Moving Averages, Patterns) — ATR provides the risk-sizing layer on top of whatever gives you the directional signal.',
  },

  fvg: {
    key: 'fvg',
    name: 'Fair Value Gaps',
    whatIsIt: 'A 3-candle price imbalance — a gap between candle 1\'s wick and candle 3\'s wick left untraded by a fast, displacement-style move on candle 2. Bullish FVG: candle 3\'s low is above candle 1\'s high. Bearish: the mirror.',
    whyTradersUseIt: 'The gap represents an area with almost no two-way trading — price moved through it too fast for real buyers and sellers to meet there, so it is considered "inefficient" and often gets revisited before the move continues.',
    whatItDetects: 'Every 3-candle imbalance in the lookback window that is large enough (relative to ATR) to count as a real institutional-style displacement, tracked as filled (price has traded back into it) or unfilled (still open).',
    whyItMatters: 'FVGs are one of the core building blocks of Smart-Money-Concepts (SMC) trading — they mark exactly where a market maker\'s fast move left a footprint, which many traders treat as a magnet / re-entry zone.',
    calculationMethod: 'For candles 1/2/3 in sequence: bullish gap = low[3] > high[1], gap zone = [high[1], low[3]]. Bearish gap = high[3] < low[1], gap zone = [high[3], low[1]]. A gap only counts if its size is at least a configured fraction of ATR (filters out tiny, meaningless gaps). "Filled" = a later candle\'s range trades back into the gap zone.',
    detectionLogic: 'Only UNFILLED gaps are drawn on the chart — filled ones are considered resolved/stale and would just clutter the view.',
    aiInvolvement: 'None in detection (pure 3-candle geometry). AI (on-demand) can reason about FVG bias alongside other enabled tools.',
    mathConcepts: 'Simple range comparison across a 3-candle window; gap "strength" scales with gap-size ÷ ATR.',
    whenToEnable: 'Especially useful alongside Market Structure / SMC-style trading, or any strategy that treats "return to inefficiency" as a valid entry trigger.',
    howToInterpret: 'An unfilled bullish FVG below current price is a potential support/re-entry zone on a pullback; an unfilled bearish FVG above price is a potential resistance/re-entry zone on a rally. More recent, larger (relative to ATR) gaps are generally more significant.',
    howToConfirm: 'Don\'t treat every FVG as guaranteed to be revisited — wait for price to actually approach the zone and show a reaction (rejection wick, momentum shift) before treating it as a trade trigger.',
    commonMistakes: [
      'Treating ALL gaps as equally significant — a tiny gap barely above the ATR threshold means much less than a large displacement gap.',
      'Assuming a gap MUST get filled before the trend continues — many gaps, especially in strong trends, never get revisited at all.',
      'Ignoring how old the gap is — very old unfilled gaps are less reliable than fresh ones.',
    ],
    bestPractices: [
      'Weight FVGs that align with the higher-timeframe trend direction more heavily.',
      'Look for FVGs that overlap with other confluence (a support level, a moving average) rather than trading them in isolation.',
      'Treat gap "fill" as a zone to react to, not an exact price to blindly buy/sell at.',
    ],
    recommendedTimeframe: 'Works on any timeframe; lower timeframes produce far more (and noisier) gaps than higher timeframes.',
    recommendedConditions: 'Most meaningful after a strong impulsive/displacement move, not in slow, grinding chop.',
    realExample: 'If price rallies hard, leaving a bullish FVG behind, then later pulls back and taps exactly into that gap zone before resuming upward with a bullish rejection candle, that is the textbook "fill the gap, continue the trend" FVG setup.',
    institutionalUse: 'The "fair value gap" framing comes directly from Smart Money Concepts / ICT-style retail-institutional trading theory — the idea being that large orders create displacement that leaves inefficient pricing behind, which smart money later uses to re-enter positions.',
    whenItFails: 'In strong, fast trends, price can leave many gaps behind that simply never fill — treating every gap as a certain revisit will produce a lot of missed continuation moves.',
    whenToAvoid: 'Avoid trading a stand-alone gap fill against a strong, established higher-timeframe trend.',
    combineWith: 'Market Structure/SMC concepts (order blocks, BOS/CHOCH), Support & Resistance (a gap that lines up with a known level is stronger), and ATR (to judge if a gap is actually significant).',
  },

  trend: {
    key: 'trend',
    name: 'Trend Line',
    whatIsIt: 'A straight line fitted through recent closing prices showing the market\'s overall direction, plus (when enough swing points exist) a channel drawn through the swing highs and swing lows.',
    whyTradersUseIt: 'To answer "what is the trend right now" at a glance, without eyeballing candles — the fitted line and its slope give an objective direction and strength reading instead of a subjective one.',
    whatItDetects: 'Trend direction (rising/falling/flat) and strength (how tightly price hugs the line, as a % fit), cross-checked against swing structure (higher-highs+higher-lows = uptrend, lower-highs+lower-lows = downtrend).',
    whyItMatters: 'Nearly every other tool\'s signal means something different depending on the prevailing trend — a support bounce in an uptrend is a higher-probability long than the same bounce during a downtrend.',
    calculationMethod: 'Least-squares regression line through closing prices over the lookback window. Slope is normalized to %/bar so it is comparable across symbols and price levels. When at least 2 swing highs and 2 swing lows exist, a channel is also fit through them (resistance line through highs, support line through lows).',
    detectionLogic: 'Direction bias comes from the swing structure (last two highs/lows) when there are enough swings; otherwise it falls back to the regression line\'s slope direction.',
    aiInvolvement: 'None in detection (pure regression + swing geometry). AI (on-demand) can reason about the trend alongside other enabled tools.',
    mathConcepts: 'Least-squares linear regression, R² (coefficient of determination, used here as "trend cleanliness"), fractal swing-point structure.',
    whenToEnable: 'Almost always — it is the fastest way to confirm you are trading with, not against, the prevailing direction.',
    howToInterpret: 'A steep slope with a high fit % is a strong, clean trend. A near-flat slope or a low fit % means price is choppy/range-bound — trend-following setups are less reliable there.',
    howToConfirm: 'Check that the swing-structure read (HH/HL or LH/LL) agrees with the regression slope — when both agree, the trend read is more reliable than either alone.',
    commonMistakes: [
      'Treating a short lookback trendline as a long-term trend call — it only describes the fitted window, not the whole history.',
      'Ignoring a low fit % (R²) — a "trend" that price barely tracks is much weaker than the slope number alone suggests.',
      'Assuming the channel boundaries are exact — like any trendline, they are a zone, not a precise price.',
    ],
    bestPractices: [
      'Favor trades in the direction of the fitted trend, not against it.',
      'Use the channel (when drawn) as dynamic support/resistance, similar to a rising/falling wedge.',
      'Recheck this tool after any large impulsive move — the fit can shift quickly once new swings form.',
    ],
    recommendedTimeframe: 'Works on any timeframe; higher timeframes give a more stable, less noisy trend read.',
    recommendedConditions: 'Most useful for confirming directional bias before taking a trend-following or pullback setup from another tool.',
    realExample: 'If the regression line is clearly rising with a high fit %, and swing structure confirms higher-highs/higher-lows, a pullback into the channel support line is a higher-conviction long than the same pullback with no trend confirmation.',
    institutionalUse: 'Systematic trend-following funds use very similar slope/regression-based trend filters to decide which direction they are even willing to trade, before any entry signal is considered.',
    whenItFails: 'In choppy, range-bound markets the fitted line has a low R² and flips direction often — treat a low-fit trendline as noise, not a real trend.',
    whenToAvoid: 'Avoid leaning on this alone right at a major structural turning point — the regression line is backward-looking and lags a genuine trend change.',
    combineWith: 'Moving Averages (does the MA stack agree with this trendline\'s direction?), Support & Resistance, and Market Structure/SMC concepts for confirmation.',
  },
}

export const TOOL_HELP_ORDER = ['trend', 'support_resistance', 'moving_averages', 'vwap', 'pivot_points', 'atr', 'fvg']
