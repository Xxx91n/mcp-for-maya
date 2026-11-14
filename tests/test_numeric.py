"""Boundary tests for the shared finite-number helper (#245)."""

import pytest

from maya_mcp_server.numeric import finite_float, finite_positive_float


@pytest.mark.parametrize(
    "bad",
    [
        True,  # bool is not a number here, even though bool subclasses int
        False,
        "1.0",  # str
        None,
        [1.0],
        {"n": 1},
        float("nan"),
        float("inf"),
        float("-inf"),
        10**400,  # int too large for float: OverflowError path
    ],
)
def test_finite_float_rejects(bad):
    assert finite_float(bad) is None


@pytest.mark.parametrize("good", [0, 1, -2, 0.0, 2.5, -0.5])
def test_finite_float_accepts_numbers(good):
    assert finite_float(good) == float(good)


@pytest.mark.parametrize(
    "bad",
    [True, False, 0, 0.0, -1, -0.5, float("nan"), float("inf"), 10**400, "1", None],
)
def test_finite_positive_float_rejects(bad):
    assert finite_positive_float(bad) is None


@pytest.mark.parametrize("good", [1, 0.5, 10**300])
def test_finite_positive_float_accepts(good):
    assert finite_positive_float(good) == float(good)
