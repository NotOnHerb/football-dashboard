"""Odds math: implied chances, decimal prices, removing the bookmaker's cut, consensus lines."""
import math, os, sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # repo root
from engine import odds  # noqa: E402


def test_implied_minus110():
    assert odds.implied(-110) == 110 / 210


def test_implied_plus_and_string():
    assert odds.implied(150) == 100 / 250
    assert odds.implied('-200') == 200 / 300


def test_decimal_plus150():
    assert odds.decimal(150) == 2.5


def test_decimal_minus200():
    assert odds.decimal(-200) == 1.5


@pytest.mark.parametrize('d,am', [(2.5, 150), (2.0, 100), (1.5, -200), (1.909, -110)])
def test_american_from_decimal(d, am):
    assert odds.american_from_decimal(d) == am


@pytest.mark.parametrize('a1,a2', [(-110, -110), (-150, 130), (-300, 240), (200, -250), (-105, -115)])
def test_shin_two_way_sums_to_one(a1, a2):
    assert math.isclose(odds.no_vig_shin(a1, a2) + odds.no_vig_shin(a2, a1), 1, abs_tol=1e-9)


def test_shin_even_market_is_half():
    assert math.isclose(odds.no_vig_shin(-110, -110), .5, abs_tol=1e-12)


def test_shin_trims_favourite_less_than_proportional():
    # Shin's method takes more of the cut out of the long shot, so the favourite keeps a bigger share
    assert odds.no_vig_shin(-300, 240) > odds.no_vig_proportional(-300, 240)


def test_shin_without_overround_is_proportional():
    assert odds.no_vig_shin(100, 100) == .5


def test_no_vig_proportional():
    assert odds.no_vig_proportional(-110, -110) == .5
    x, y = odds.implied(-150), odds.implied(130)
    assert odds.no_vig_proportional(-150, 130) == x / (x + y)


def test_consensus_line_most_common_then_closest_to_median():
    assert odds.consensus_line([-3, -3, -2.5, None]) == -3
    # tie on count: the one nearer the median wins
    assert odds.consensus_line([44.5, 45.5, 45, 45, 44.5]) == 45
    assert odds.consensus_line([1, 2, 2, 9, 9]) == 2
    assert odds.consensus_line([None, None]) is None
    assert odds.consensus_line([]) is None


def test_median():
    assert odds.median([3, 1, 2]) == 2
    assert odds.median([]) is None


def test_normal_cdf():
    assert odds.normal_cdf(0) == .5
    assert math.isclose(odds.normal_cdf(1.96), .975, abs_tol=1e-3)
