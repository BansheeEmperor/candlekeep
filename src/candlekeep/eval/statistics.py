"""Bootstrap confidence intervals for benchmark metrics."""
import numpy as np
from typing import List, Tuple


def bootstrap_ci(
    scores: List[float],
    n_bootstrap: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Compute bootstrap confidence interval for a metric.

    Args:
        scores: Per-query metric values.
        n_bootstrap: Number of bootstrap resamples.
        ci: Confidence level (0.95 = 95%).
        seed: RNG seed for reproducibility.

    Returns:
        (mean, lower_bound, upper_bound)
    """
    if not scores:
        return (0.0, 0.0, 0.0)

    arr = np.array(scores, dtype=float)
    observed_mean = float(np.mean(arr))

    if len(arr) == 1:
        return (observed_mean, observed_mean, observed_mean)

    rng = np.random.default_rng(seed)
    boot_means = np.array([
        np.mean(rng.choice(arr, size=len(arr), replace=True))
        for _ in range(n_bootstrap)
    ])

    alpha = 1.0 - ci
    lower = float(np.percentile(boot_means, alpha / 2 * 100))
    upper = float(np.percentile(boot_means, (1 - alpha / 2) * 100))

    return (observed_mean, lower, upper)
