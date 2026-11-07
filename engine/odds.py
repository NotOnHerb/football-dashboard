"""Odds math: American prices to chances and decimal payouts, removing the bookmaker's cut, consensus lines."""
import statistics
from math import erf, sqrt


def implied(american):
    """Chance a price implies, cut included (-110 -> 0.524)."""
    a = float(american); return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def decimal(american):
    """Decimal payout per unit staked, stake included (+150 -> 2.5)."""
    a = american
    return (1 + a / 100) if a > 0 else (1 - 100 / a)


def american_from_decimal(d):
    """American price for a decimal payout (2.5 -> +150, 1.5 -> -200)."""
    return int(round((d - 1) * 100)) if d >= 2 else int(round(-100 / (d - 1)))


def no_vig_shin(a1, a2):
    """Chance of side 1 with the bookmaker's cut removed, Shin's method (it doesn't over-credit long shots the way a
    plain proportional split does)."""
    q = [implied(a1), implied(a2)]; S = sum(q)
    if S <= 1: return q[0] / S
    pr_ = lambda z: [((z * z + 4 * (1 - z) * x * x / S) ** .5 - z) / (2 * (1 - z)) for x in q]
    lo, hi = 0.0, 0.4
    for _ in range(60):
        mid = (lo + hi) / 2
        if sum(pr_(mid)) > 1: lo = mid
        else: hi = mid
    r = pr_((lo + hi) / 2); return r[0] / sum(r)


def no_vig_proportional(a1, a2):
    """Chance of side 1 with the cut split in proportion to the two implied chances."""
    x, y = implied(a1), implied(a2)
    return x / (x + y)


def median(xs):
    """Median, or None for an empty list."""
    return statistics.median(xs) if xs else None


def consensus_line(xs):
    """The line most books post (ties go to the one nearest the median); None values are ignored."""
    xs = [x for x in xs if x is not None]
    return max(set(xs), key=lambda x: (xs.count(x), -abs(x - statistics.median(xs)))) if xs else None


def normal_cdf(x):
    """Standard normal cumulative distribution."""
    return .5 * (1 + erf(x / sqrt(2)))
