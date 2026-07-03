import numpy as np

from backend.app.core.pattern_config import pattern_config


class TrendlineFit:

    def __init__(self, slope: float, intercept: float, r_squared: float, points: list):
        self.slope = slope
        self.intercept = intercept
        self.r_squared = r_squared
        self.points = points  # the (index, price) pairs used to fit

    def value_at(self, index: int) -> float:
        return self.slope * index + self.intercept


def fit_trendline(indices: list[int], prices: list[float]) -> TrendlineFit:
    """Least-squares line through the given (bar_index, price) points."""
    x = np.array(indices, dtype=float)
    y = np.array(prices, dtype=float)
    if len(x) < 2:
        raise ValueError("Need at least 2 points to fit a trendline")

    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 1.0

    return TrendlineFit(float(slope), float(intercept), r_squared, list(zip(indices, prices)))


def slope_pct_per_bar(fit: TrendlineFit, reference_price: float) -> float:
    """Slope normalized to % price change per bar — comparable across symbols/price levels."""
    if reference_price <= 0:
        return 0.0
    return (fit.slope / reference_price) * 100


def classify_slope(slope_pct: float, tolerance_pct: float = None) -> str:
    tol = tolerance_pct if tolerance_pct is not None else pattern_config.TRIANGLE_FLAT_SLOPE_TOLERANCE_PCT
    if abs(slope_pct) <= tol:
        return "FLAT"
    return "RISING" if slope_pct > 0 else "FALLING"
