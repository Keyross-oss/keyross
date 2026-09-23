"""The statistics of the benchmark, in the standard library so anyone can check them: exact McNemar test on paired outcomes,
Wilson intervals for proportions, a seeded paired bootstrap for differences of means."""
from __future__ import annotations

import math
import random
from typing import Sequence

Z95 = 1.959963984540054


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value. b: pairs where only the first arm succeeds; c: only the second."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def wilson(k: int, n: int) -> tuple[float, float]:
    """95 % Wilson score interval for k successes out of n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + Z95 ** 2 / n
    centre = (p + Z95 ** 2 / (2 * n)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95 ** 2 / (4 * n ** 2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def paired_bootstrap(diffs: Sequence[float], *, resamples: int = 10_000, seed: int = 7) -> tuple[float, float, float]:
    """Mean of paired differences and its 95 % percentile interval (pairs resampled with replacement, seeded)."""
    if not diffs:
        return (float("nan"), float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples))
    return (sum(diffs) / n, means[int(0.025 * resamples)], means[int(0.975 * resamples) - 1])
