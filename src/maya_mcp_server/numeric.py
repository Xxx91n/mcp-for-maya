"""Shared finite-number validation helpers.

One implementation for the "finite, non-boolean numeric value" check used
across the server-side modules, so overflow and type handling cannot drift
between call sites again (issue #245).
"""

from __future__ import annotations

import math
from typing import Any


def finite_float(value: Any) -> float | None:
    """Convert a numeric value to a finite float, rejecting bools and huge ints.

    Returns None for bool, non-(int, float) values, NaN/inf, and ints too
    large for float() (OverflowError) — never raises.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        out = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def finite_positive_float(value: Any) -> float | None:
    """A finite float that is also strictly positive, else None."""
    num = finite_float(value)
    if num is None or num <= 0:
        return None
    return num
