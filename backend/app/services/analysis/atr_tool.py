import pandas as pd

from backend.app.core.analysis_config import analysis_config
from backend.app.schemas.analysis_tool import AnalysisToolResult
from backend.app.schemas.pattern import ChartAnnotations, LevelAnnotation, PatternDirection
from backend.app.services.analysis.base_analysis_tool import BaseAnalysisTool
from backend.app.services.indicator_service import IndicatorService
from backend.app.services.pattern.pattern_utils import now_iso


class ATRTool(BaseAnalysisTool):
    """
    Current volatility (ATR) + a volatility classification (Low/Medium/High,
    from ATR as % of price) + suggested stop-loss/take-profit levels for both
    a long and a short at the current price, ATR-scaled. Direction-neutral by
    nature — this tool measures risk/volatility, not market bias.
    """

    key = "atr"
    name = "Average True Range"

    def __init__(self):
        self.indicators = IndicatorService()

    def analyze(self, df: pd.DataFrame, symbol: str, interval: str) -> AnalysisToolResult:
        cfg = analysis_config
        current_price = float(df["close"].iloc[-1])
        atr = self.indicators.calculate_atr_at_period(df, cfg.ATR_PERIOD)

        if not atr or atr <= 0:
            return AnalysisToolResult(
                tool_key=self.key, tool_name=self.name, symbol=symbol, interval=interval,
                bias=PatternDirection.NEUTRAL, summary="ATR unavailable",
                annotations=ChartAnnotations(), last_updated=now_iso(), error="ATR could not be computed",
            )

        atr_pct = atr / current_price * 100
        if atr_pct < cfg.ATR_LOW_VOL_PCT:
            volatility = "LOW"
        elif atr_pct > cfg.ATR_HIGH_VOL_PCT:
            volatility = "HIGH"
        else:
            volatility = "MEDIUM"

        long_sl = current_price - atr * cfg.ATR_SL_MULTIPLIER
        long_tp = current_price + atr * cfg.ATR_TP_MULTIPLIER
        short_sl = current_price + atr * cfg.ATR_SL_MULTIPLIER
        short_tp = current_price - atr * cfg.ATR_TP_MULTIPLIER
        risk_reward = round(cfg.ATR_TP_MULTIPLIER / cfg.ATR_SL_MULTIPLIER, 2)

        annotations = ChartAnnotations(
            levels=[
                LevelAnnotation(label="long_stop_loss", price=round(long_sl, 8)),
                LevelAnnotation(label="long_take_profit", price=round(long_tp, 8)),
                LevelAnnotation(label="short_stop_loss", price=round(short_sl, 8)),
                LevelAnnotation(label="short_take_profit", price=round(short_tp, 8)),
            ],
        )

        summary = f"ATR({cfg.ATR_PERIOD}) = {atr:.2f} ({atr_pct:.2f}% of price) — {volatility} volatility."

        return AnalysisToolResult(
            tool_key=self.key, tool_name=self.name, symbol=symbol, interval=interval,
            bias=PatternDirection.NEUTRAL, summary=summary,
            data={
                "atr": round(atr, 8), "atr_pct_of_price": round(atr_pct, 4), "volatility": volatility,
                "long_stop_loss": round(long_sl, 8), "long_take_profit": round(long_tp, 8),
                "short_stop_loss": round(short_sl, 8), "short_take_profit": round(short_tp, 8),
                "risk_reward": risk_reward,
            },
            annotations=annotations, last_updated=now_iso(),
        )
