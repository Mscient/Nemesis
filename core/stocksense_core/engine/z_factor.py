"""z-factor lookup via inverse normal CDF (scipy)."""
from scipy.stats import norm


def service_level_to_z(p: float) -> float:
    """Return z-factor for a given service level probability p in (0, 1)."""
    if not (0 < p < 1):
        raise ValueError(f"service_level must be in (0, 1), got {p}")
    return float(norm.ppf(p))
