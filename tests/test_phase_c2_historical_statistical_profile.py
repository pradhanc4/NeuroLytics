from database.engine import SessionLocal
from analytics.historical_statistical_profile import (
    PROFILE_VERSION,
    build_historical_statistical_profile,
    write_historical_statistical_profile,
)


def test_phase_c2_profile():
    db = SessionLocal()
    try:
        profile = build_historical_statistical_profile(db, 1)
        assert profile.version == PROFILE_VERSION
        assert profile.record_count == 1990
        assert profile.first_date == "2021-02-01"
        assert profile.last_date == "2026-07-31"
        assert set(profile.column_statistics) == {f"col{i}" for i in range(1, 9)}
        assert set(profile.digit_distributions) == set(profile.column_statistics)
        for distribution in profile.digit_distributions.values():
            assert sum(item["count"] for item in distribution.values()) == 1990
        assert set(profile.relationships) == {
            "open_to_jodi_first",
            "open_to_jodi_second",
            "jodi_first_to_jodi_second",
            "jodi_first_to_close_first",
            "jodi_second_to_close_first",
        }
        assert sum(profile.family_frequencies["jodi"].values()) == 1990
        assert sum(profile.family_frequencies["first_panel_digit_family"].values()) == 1990
        assert sum(profile.family_frequencies["second_panel_digit_family"].values()) == 1990
        path = write_historical_statistical_profile(profile)
        assert path.exists()
    finally:
        db.close()
