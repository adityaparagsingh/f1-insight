"""Small statistics helpers used across analytics + mining."""
from __future__ import annotations

import math
from typing import Iterable, Optional, Sequence


def pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """Pearson correlation coefficient; None when undefined."""
    pairs = [
        (float(x), float(y))
        for x, y in zip(xs, ys)
        if x is not None and y is not None
    ]
    n = len(pairs)
    if n < 3:
        return None
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    num = sum((x - mx) * (y - my) for x, y in pairs)
    dx = math.sqrt(sum((x - mx) ** 2 for x, _ in pairs))
    dy = math.sqrt(sum((y - my) ** 2 for _, y in pairs))
    if dx == 0 or dy == 0:
        return None
    return round(num / (dx * dy), 4)


def safe_rate(part: Optional[float], whole: Optional[float]) -> Optional[float]:
    if not whole:
        return None
    return round((part or 0) / whole, 4)
