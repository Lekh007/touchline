"""Hand-computed fixtures, not snapshot tests.

Each expected number was derived by hand from the model's definition, so a
regression here means the *model* changed, not merely the code around it.
Conservation (credit sums to revenue) is asserted for every model on a
multi-conversion mix.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from touchline.attribution import (
    ConversionPath,
    Touchpoint,
    conservation,
    first_touch,
    last_touch,
    linear,
    time_decay,
)

T0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)


def path(touch_offsets_days: tuple[float, ...], *, revenue: float = 300.0) -> ConversionPath:
    """A conversion at T0 with touches at whole/half-day offsets before it."""
    return ConversionPath(
        conversion_id="c1",
        revenue=revenue,
        converted_at=T0,
        touchpoints=tuple(
            Touchpoint(channel=f"ch{i}", ts=T0 - timedelta(days=offset))
            for i, offset in enumerate(touch_offsets_days)
        ),
    )


class TestLastAndFirstTouch:
    def test_last_touch_gives_everything_to_the_final_channel(self) -> None:
        credits = last_touch([path((2.0, 1.0, 0.0))])
        assert credits == {"ch2": 300.0}

    def test_first_touch_gives_everything_to_the_introducing_channel(self) -> None:
        credits = first_touch([path((2.0, 1.0, 0.0))])
        assert credits == {"ch0": 300.0}


class TestLinear:
    def test_credit_splits_equally_across_the_path(self) -> None:
        credits = linear([path((2.0, 1.0, 0.0))])
        assert credits == {"ch0": 100.0, "ch1": 100.0, "ch2": 100.0}

    def test_a_single_touch_path_is_the_whole_revenue(self) -> None:
        credits = linear([path((0.0,))])
        assert credits == {"ch0": 300.0}


class TestTimeDecay:
    def test_half_life_weights_are_powers_of_one_half(self) -> None:
        # Touches 2, 1, 0 days before conversion, half-life 1 day:
        # weights 0.25, 0.5, 1.0 -> shares 1/7, 2/7, 4/7 of 300.
        credits = time_decay([path((2.0, 1.0, 0.0))], half_life_days=1.0)
        assert credits["ch0"] == pytest.approx(300.0 * 1 / 7)
        assert credits["ch1"] == pytest.approx(300.0 * 2 / 7)
        assert credits["ch2"] == pytest.approx(300.0 * 4 / 7)

    def test_a_touch_at_the_conversion_moment_caries_full_weight(self) -> None:
        credits = time_decay([path((0.0,))], half_life_days=7.0)
        assert credits["ch0"] == pytest.approx(300.0)

    def test_non_positive_half_life_is_refused(self) -> None:
        with pytest.raises(ValueError, match="half_life_days"):
            time_decay([path((0.0,))], half_life_days=0.0)


class TestConservation:
    def test_every_model_accounts_for_every_rupee(self) -> None:
        paths = [
            path((2.0, 1.0, 0.0), revenue=300.0),
            path((0.5, 0.0), revenue=120.5),
            path((9.0, 4.0, 2.0, 1.0, 0.0), revenue=79.5),
        ]
        for model in (last_touch, first_touch, linear):
            credits = model(paths)
            assert conservation(paths, credits) == pytest.approx(0.0)
        decayed = time_decay(paths, half_life_days=3.0)
        assert conservation(paths, decayed) == pytest.approx(0.0)

    def test_channels_accumulate_across_conversions(self) -> None:
        paths = [path((1.0, 0.0), revenue=100.0), path((0.0,), revenue=50.0)]
        credits = last_touch(paths)
        assert credits == {"ch1": 100.0, "ch0": 50.0}


class TestPathValidity:
    def test_a_path_without_touchpoints_is_refused(self) -> None:
        with pytest.raises(ValueError, match="no touchpoints"):
            ConversionPath(conversion_id="c", revenue=1.0, converted_at=T0, touchpoints=())

    def test_a_touch_after_the_conversion_is_refused(self) -> None:
        late = Touchpoint(channel="ch", ts=T0 + timedelta(days=1))
        with pytest.raises(ValueError, match="after the conversion"):
            ConversionPath(conversion_id="c", revenue=1.0, converted_at=T0, touchpoints=(late,))
