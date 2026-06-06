"""
Estimates throw distance from ball landing coordinates to home plate.

Approximation note (stated explicitly per project methodology):
  Statcast hc_x / hc_y are pixel coordinates on a ~250×250 field diagram.
  Home plate sits at approximately (125.42, 198.27) in those units.
  We use a scale of 2.5 ft/unit, calibrated so deep-CF hits (hc_y ≈ 30)
  give ~420 ft throw distance, matching known park dimensions.
  This is an estimate — real throw distance is not in public Statcast data.
"""
import math
import pandas as pd

HOME_HCX: float = 125.42
HOME_HCY: float = 198.27
FT_PER_UNIT: float = 2.5


def throw_distance_to_home(hc_x: float, hc_y: float) -> float:
    """Euclidean distance (approximate feet) from ball landing spot to home plate."""
    dx = (hc_x - HOME_HCX) * FT_PER_UNIT
    dy = (HOME_HCY - hc_y) * FT_PER_UNIT
    return math.hypot(dx, dy)


def validate_distances(series: pd.Series) -> None:
    """Fail loudly if computed distances look implausible for MLB outfield plays."""
    p5  = series.quantile(0.05)
    med = series.median()
    p95 = series.quantile(0.95)
    print(f"Throw distance (ft): p5={p5:.0f}  median={med:.0f}  p95={p95:.0f}")
    if not (150 <= med <= 400):
        raise ValueError(
            f"Median throw distance {med:.0f} ft outside expected 150–400 ft. "
            "Check HOME_HCX / HOME_HCY / FT_PER_UNIT constants."
        )
