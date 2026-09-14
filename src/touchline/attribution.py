"""Deterministic attribution.

Every number Touchline reports about *credit* — which channel drove which
share of revenue — comes from this module and nowhere else. An LLM may narrate
these numbers, question them, or refuse to interpret them; it may never
produce one. That boundary is the same discipline BondLens applies to
financial facts: the model investigates and explains, Python decides.

All three models share one contract, and `conservation` is its statement:
credit assigned across channels sums to the revenue converted, to floating
point. An attribution model that leaks or invents revenue is worse than
useless — it looks plausible on a dashboard.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Touchpoint:
    """One marketing interaction on the path to a conversion."""

    channel: str
    ts: datetime


@dataclass(frozen=True)
class ConversionPath:
    """A conversion and the ordered touchpoints that led to it."""

    conversion_id: str
    revenue: float
    converted_at: datetime
    touchpoints: tuple[Touchpoint, ...]

    def __post_init__(self) -> None:
        if not self.touchpoints:
            raise ValueError(f"conversion {self.conversion_id!r} has no touchpoints")
        if any(tp.ts > self.converted_at for tp in self.touchpoints):
            raise ValueError(f"conversion {self.conversion_id!r} has a touchpoint after the conversion")


Credits = dict[str, float]
"""Channel -> credited revenue. Sums to the input revenue; see `conservation`."""


def _add(credits: Credits, channel: str, amount: float) -> None:
    credits[channel] = credits.get(channel, 0.0) + amount


def conservation(paths: Iterable[ConversionPath], credits: Credits) -> float:
    """Total revenue minus total credited. Zero (to float noise) for a correct model."""
    return sum(p.revenue for p in paths) - sum(credits.values())


def last_touch(paths: Iterable[ConversionPath]) -> Credits:
    """100% of a conversion's revenue to the final touchpoint."""
    credits: Credits = {}
    for path in paths:
        _add(credits, path.touchpoints[-1].channel, path.revenue)
    return credits


def first_touch(paths: Iterable[ConversionPath]) -> Credits:
    """100% of a conversion's revenue to the first touchpoint."""
    credits: Credits = {}
    for path in paths:
        _add(credits, path.touchpoints[0].channel, path.revenue)
    return credits


def linear(paths: Iterable[ConversionPath]) -> Credits:
    """A conversion's revenue split equally across every touchpoint on its path."""
    credits: Credits = {}
    for path in paths:
        share = path.revenue / len(path.touchpoints)
        for touchpoint in path.touchpoints:
            _add(credits, touchpoint.channel, share)
    return credits


def time_decay(paths: Iterable[ConversionPath], *, half_life_days: float = 7.0) -> Credits:
    """Revenue split by exponential recency, weight 0.5^(days before conversion / half-life).

    The half-life is the product's honesty knob: at 7 days a touch from a week
    ago counts half a fresh one. Touches *at* the conversion moment carry full
    weight, which is what makes last-touch the half_life -> 0 limit.
    """
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    credits: Credits = {}
    for path in paths:
        weights = [
            0.5 ** ((path.converted_at - touchpoint.ts).total_seconds() / 86_400.0 / half_life_days)
            for touchpoint in path.touchpoints
        ]
        total = sum(weights)
        for touchpoint, weight in zip(path.touchpoints, weights, strict=True):
            _add(credits, touchpoint.channel, path.revenue * weight / total)
    return credits
