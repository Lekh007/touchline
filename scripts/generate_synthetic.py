"""Seeded synthetic marketing warehouse with planted ground truth.

Deterministic: the same seed produces the same warehouse, so eval results are
comparable across runs and across machines.

The planted truth (what makes this an eval corpus and not just fake data):
each channel has a hidden `quality` multiplier on conversion probability.
`search` converts best, `social` second, `email` and `display` are weak, and
`referral` is rare but excellent. An analyst (human or agent) reading the
output should be able to *discover* these orderings from attribution and RoI —
which is exactly what the wave-2 eval set grades.

The generator also plants a trap: `display` has high spend and high
top-of-funnel volume but a poor quality multiplier. A last-touch-only view of
this warehouse overstates display's contribution on late-stage paths and
understates search's introduction work. The correct interpretation requires
comparing models — precisely the analysis the product exists to produce.
"""

from __future__ import annotations

import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from touchline.db import Warehouse

# channel: (share of first touches, quality multiplier on final-conversion odds)
CHANNELS: dict[str, tuple[float, float]] = {
    "search": (0.30, 1.60),
    "social": (0.25, 1.20),
    "email": (0.20, 0.80),
    "display": (0.20, 0.55),
    "referral": (0.05, 1.90),
}
USERS = 500
DAYS = 60
BASE_CONVERSION_ODDS = 0.06
MEAN_REVENUE = 850.0
COST_PER_TOUCH: dict[str, float] = {
    "search": 22.0,
    "social": 14.0,
    "email": 3.0,
    "display": 9.0,
    "referral": 1.5,
}


def generate(path: Path, *, seed: int = 20260915) -> None:
    rng = random.Random(seed)
    start = datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC)
    if path.exists():
        path.unlink()

    with Warehouse(path) as warehouse:
        conversion_seq = 0
        for user in range(USERS):
            first_day = rng.randint(0, DAYS - 2)
            # How many touches this user's journey has: 1-6, biased short.
            touch_count = min(6, max(1, int(rng.random() * rng.random() * 6) + 1))
            day = first_day
            touches: list[tuple[str, datetime]] = []
            for i in range(touch_count):
                if i == 0:
                    channel = _pick_first_channel(rng)
                else:
                    # Repeat-purchase bias: stickiness toward channels already seen.
                    channel = _pick_next_channel(rng, [c for c, _ in touches])
                hour = rng.randint(8, 23)
                touches.append((channel, start + timedelta(days=day, hours=hour)))
                day = min(day + rng.randint(0, 4), DAYS - 1)

            # Final touch decides conversion odds, scaled by channel quality.
            final_channel = touches[-1][0]
            odds = BASE_CONVERSION_ODDS * CHANNELS[final_channel][1]
            if rng.random() < odds:
                conversion_seq += 1
                revenue = round(rng.gauss(MEAN_REVENUE, MEAN_REVENUE / 3), 2)
                converted_at = touches[-1][1] + timedelta(hours=rng.randint(1, 6))
                warehouse.record_conversion(
                    conversion_id=f"c{conversion_seq:05d}",
                    user_id=f"u{user:05d}",
                    revenue=max(revenue, 50.0),
                    converted_at=converted_at,
                    touchpoints=touches,
                )

        for channel, (_, _) in CHANNELS.items():
            for day_offset in range(DAYS):
                # Display buys broadly: flat high spend. Search follows weekday volume.
                base = COST_PER_TOUCH[channel] * rng.uniform(0.8, 1.2)
                if channel == "display":
                    base *= 3.0
                warehouse.record_spend(
                    channel, (start + timedelta(days=day_offset)).date().isoformat(), round(base, 2)
                )

        print(f"users={USERS} conversions={warehouse.conversion_count()} -> {path}")


def _pick_first_channel(rng: random.Random) -> str:
    population = [(channel, share) for channel, (share, _) in CHANNELS.items()]
    return rng.choices([c for c, _ in population], weights=[w for _, w in population])[0]


def _pick_next_channel(rng: random.Random, seen: list[str]) -> str:
    # Slight stickiness toward previously seen channels, otherwise first-touch shares.
    population = [(channel, share * (1.5 if channel in seen else 1.0)) for channel, (share, _) in CHANNELS.items()]
    return rng.choices([c for c, _ in population], weights=[w for _, w in population])[0]


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/marketing.duckdb")
    generate(target)
