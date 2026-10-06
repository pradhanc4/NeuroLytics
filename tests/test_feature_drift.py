from datetime import date, timedelta

import pytest

from features.feature_artifact import FeatureArtifact
from features.feature_schema import FeatureSchema
from features.feature_versioning import FeatureVersionIdentity
from analytics.feature_drift import (
    DEFAULT_BINS,
    FEATURE_DRIFT_VERSION,
    FeatureDriftRule,
    build_feature_drift_report,
    feature_drift_feature_names,
    feature_drift_observations,
    feature_drift_summary,
    validate_feature_drift_report,
)


def make_source(
    first=(1.0, 1.1, 0.9, 1.0),
    second=(1.0, 1.1, 0.9, 1.0),
    name="f1",
    data_type="float",
):
    values = list(first) + list(second)
    schema = FeatureSchema(
        name, "54-test", "lag", "test", "col1", 1, 1,
        "test", "result_date < target_date", data_type
    )
    identity = FeatureVersionIdentity(
        "54-test", "feature-test", "sha256", "test"
    )
    result = []
    for index, value in enumerate(values):
        day = index if index < len(first) else 14 + index - len(first)
        result.append(
            FeatureArtifact(
                date(2026, 1, 1) + timedelta(days=day),
                "54-test",
                (name,),
                {name: value},
                (schema,),
                identity,
                "VALID",
                "CLEAN",
            )
        )
    return tuple(result)


def test_version_and_defaults():
    report = build_feature_drift_report(make_source())
    assert report.version == FEATURE_DRIFT_VERSION
    assert report.bin_count == DEFAULT_BINS
    assert report.period_days == 7


def test_valid_and_deterministic():
    source = make_source()
    first = build_feature_drift_report(source)
    second = build_feature_drift_report(source)
    assert validate_feature_drift_report(first).is_valid
    assert first.report_identity == second.report_identity


def test_stable_distribution_not_drifted():
    report = build_feature_drift_report(make_source())
    assert report.drifted is False
    assert report.drifted_features == ()


def test_shifted_distribution_detected():
    report = build_feature_drift_report(
        make_source(second=(9.0, 9.1, 8.9, 9.0))
    )
    assert report.drifted is True
    assert report.drifted_features == ("f1",)


def test_custom_high_threshold_suppresses_drift():
    report = build_feature_drift_report(
        make_source(second=(9.0, 9.1, 8.9, 9.0)),
        rules=(FeatureDriftRule("f1", 100.0),),
    )
    assert report.drifted is False


def test_accessor_names():
    report = build_feature_drift_report(make_source())
    assert feature_drift_feature_names(report) == ("f1",)


def test_accessor_observations():
    report = build_feature_drift_report(make_source())
    observations = feature_drift_observations(report, "f1")
    assert len(observations) == 1
    assert observations[0].baseline_count == 4
    assert observations[0].comparison_count == 4

def test_summary_is_valid():
    report = build_feature_drift_report(make_source())
    summary = feature_drift_summary(report)
    assert summary["status"] == "VALID"
    assert summary["comparisons"] == 1


def test_unknown_feature_rejected():
    with pytest.raises(ValueError):
        build_feature_drift_report(
            make_source(), rules=(FeatureDriftRule("missing"),)
        )


def test_duplicate_rules_rejected():
    with pytest.raises(ValueError):
        build_feature_drift_report(
            make_source(),
            rules=(FeatureDriftRule("f1"), FeatureDriftRule("f1")),
        )


@pytest.mark.parametrize("threshold", [0.0, -1.0, float("inf"), float("nan")])
def test_invalid_threshold_rejected(threshold):
    with pytest.raises(ValueError):
        build_feature_drift_report(
            make_source(),
            rules=(FeatureDriftRule("f1", threshold),),
        )


@pytest.mark.parametrize("period_days", [0, -1, True, 1.5])
def test_invalid_period_rejected(period_days):
    with pytest.raises(ValueError):
        build_feature_drift_report(make_source(), period_days=period_days)


@pytest.mark.parametrize("bin_count", [0, 1, -2, True, 1.5])
def test_invalid_bins_rejected(bin_count):
    with pytest.raises(ValueError):
        build_feature_drift_report(make_source(), bin_count=bin_count)


def test_requires_two_periods():
    source = make_source(second=())
    with pytest.raises(ValueError):
        build_feature_drift_report(source)


def test_requires_two_artifacts():
    source = make_source()[:1]
    with pytest.raises(ValueError):
        build_feature_drift_report(source)


def test_duplicate_dates_rejected():
    source = list(make_source())
    item = source[1]
    source[1] = FeatureArtifact(
        source[0].target_date, item.feature_version, item.feature_names,
        item.feature_values, item.schemas, item.version_identity,
        "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_feature_drift_report(source)


def test_mismatched_version_rejected():
    source = list(make_source())
    item = source[1]
    source[1] = FeatureArtifact(
        item.target_date, "other", item.feature_names, item.feature_values,
        item.schemas, item.version_identity, "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_feature_drift_report(source)


def test_mismatched_feature_names_rejected():
    source = list(make_source())
    item = source[1]
    schema = FeatureSchema(
        "other", "54-test", "lag", "test", "col1", 1, 1,
        "other", "result_date < target_date", "float"
    )
    source[1] = FeatureArtifact(
        item.target_date, "54-test", ("other",), {"other": 1.0},
        (schema,), item.version_identity, "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_feature_drift_report(source)

def test_invalid_artifact_rejected():
    source = list(make_source())
    item = source[0]
    source[0] = FeatureArtifact(
        item.target_date, item.feature_version, item.feature_names,
        item.feature_values, item.schemas, item.version_identity,
        "INVALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_feature_drift_report(source)


def test_non_numeric_value_rejected():
    source = list(make_source())
    item = source[-1]
    source[-1] = FeatureArtifact(
        item.target_date, item.feature_version, item.feature_names,
        {"f1": "bad"}, item.schemas, item.version_identity,
        "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_feature_drift_report(source)


def test_boolean_value_rejected():
    source = list(make_source())
    item = source[-1]
    source[-1] = FeatureArtifact(
        item.target_date, item.feature_version, item.feature_names,
        {"f1": True}, item.schemas, item.version_identity,
        "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_feature_drift_report(source)


def test_nan_value_rejected():
    source = list(make_source())
    item = source[-1]
    source[-1] = FeatureArtifact(
        item.target_date, item.feature_version, item.feature_names,
        {"f1": float("nan")}, item.schemas, item.version_identity,
        "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_feature_drift_report(source)


def test_none_values_are_excluded_and_missing_rate_recorded():
    source = list(make_source())
    item = source[-1]
    source[-1] = FeatureArtifact(
        item.target_date, item.feature_version, item.feature_names,
        {"f1": None}, item.schemas, item.version_identity,
        "VALID", "CLEAN"
    )
    report = build_feature_drift_report(source)
    observation = feature_drift_observations(report, "f1")[0]
    assert observation.comparison_count == 3
    assert observation.comparison_missing_rate == 0.25


def test_zero_values_are_supported():
    report = build_feature_drift_report(
        make_source(
            first=(0.0, 0.0, 0.0, 0.0),
            second=(0.0, 0.0, 0.0, 0.0),
        )
    )
    assert validate_feature_drift_report(report).is_valid
    assert feature_drift_observations(report, "f1")[0].psi == 0.0


def test_single_numeric_value_has_zero_std():
    report = build_feature_drift_report(
        make_source(first=(1.0,), second=(1.0,))
    )
    observation = feature_drift_observations(report, "f1")[0]
    assert observation.baseline_std == 0.0
    assert observation.comparison_std == 0.0


def test_all_missing_baseline_rejected():
    source = list(make_source())
    for index in range(4):
        item = source[index]
        source[index] = FeatureArtifact(
            item.target_date, item.feature_version, item.feature_names,
            {"f1": None}, item.schemas, item.version_identity,
            "VALID", "CLEAN"
        )
    with pytest.raises(ValueError):
        build_feature_drift_report(source)

def test_all_missing_comparison_rejected():
    source = list(make_source())
    for index in range(4, 8):
        item = source[index]
        source[index] = FeatureArtifact(
            item.target_date, item.feature_version, item.feature_names,
            {"f1": None}, item.schemas, item.version_identity,
            "VALID", "CLEAN"
        )
    with pytest.raises(ValueError):
        build_feature_drift_report(source)


def test_non_numeric_rule_selected_rejected_by_default():
    with pytest.raises(ValueError):
        build_feature_drift_report(
            make_source(data_type="string")
        )


def test_explicit_rule_allows_schema_declared_string_but_numeric_values():
    report = build_feature_drift_report(
        make_source(data_type="string"),
        rules=(FeatureDriftRule("f1"),),
    )
    assert validate_feature_drift_report(report).is_valid


def test_multiple_features_supported():
    base = make_source()
    schema = FeatureSchema(
        "f2", "54-test", "lag", "test", "col2", 1, 1,
        "second", "result_date < target_date", "float"
    )
    source = tuple(
        FeatureArtifact(
            item.target_date,
            item.feature_version,
            ("f1", "f2"),
            {
                "f1": item.feature_values["f1"],
                "f2": item.feature_values["f1"] * 2,
            },
            (item.schemas[0], schema),
            item.version_identity,
            "VALID",
            "CLEAN",
        )
        for item in base
    )
    report = build_feature_drift_report(source)
    assert report.drifted is False
    assert len(report.rules) == 2


def test_multiple_features_one_drifted():
    base = make_source(second=(9.0, 9.1, 8.9, 9.0))
    schema = FeatureSchema(
        "f2", "54-test", "lag", "test", "col2", 1, 1,
        "second", "result_date < target_date", "float"
    )
    source = tuple(
        FeatureArtifact(
            item.target_date,
            item.feature_version,
            ("f1", "f2"),
            {
                "f1": item.feature_values["f1"],
                "f2": 2.0,
            },
            (item.schemas[0], schema),
            item.version_identity,
            "VALID",
            "CLEAN",
        )
        for item in base
    )
    report = build_feature_drift_report(source)
    assert report.drifted_features == ("f1",)
    assert report.drifted_periods == (("f1", date(2026, 1, 15)),)


def test_report_identity_changes_with_threshold():
    source = make_source(second=(9.0, 9.1, 8.9, 9.0))
    a = build_feature_drift_report(source)
    b = build_feature_drift_report(
        source, rules=(FeatureDriftRule("f1", 0.3),)
    )
    assert a.report_identity != b.report_identity


def test_report_identity_changes_with_bins():
    source = make_source(second=(9.0, 9.1, 8.9, 9.0))
    a = build_feature_drift_report(source, bin_count=5)
    b = build_feature_drift_report(source, bin_count=10)
    assert a.report_identity != b.report_identity

def test_report_identity_changes_with_period():
    source = make_source(second=(9.0, 9.1, 8.9, 9.0))
    a = build_feature_drift_report(source, period_days=7)
    b = build_feature_drift_report(source, period_days=4)
    assert a.report_identity != b.report_identity


def test_custom_threshold_is_inclusive():
    source = make_source(second=(9.0, 9.1, 8.9, 9.0))
    base = build_feature_drift_report(source)
    psi = feature_drift_observations(base, "f1")[0].psi
    report = build_feature_drift_report(
        source, rules=(FeatureDriftRule("f1", psi),)
    )
    assert report.drifted is True


def test_validation_detects_invalid_version():
    report = build_feature_drift_report(make_source())
    invalid = report.__class__(
        "bad", report.feature_version, report.source_artifact_count,
        report.source_feature_names, report.period_days, report.rules,
        report.bin_count, report.observations, report.drifted_features,
        report.drifted_periods, report.drifted, report.report_identity
    )
    assert not validate_feature_drift_report(invalid).is_valid


def test_validation_detects_invalid_drift_flag():
    report = build_feature_drift_report(make_source())
    observation = report.observations[0]
    changed = observation.__class__(
        observation.feature_name, observation.baseline_period_start,
        observation.comparison_period_start, observation.baseline_count,
        observation.comparison_count, observation.baseline_missing_rate,
        observation.comparison_missing_rate, observation.baseline_mean,
        observation.comparison_mean, observation.baseline_std,
        observation.comparison_std, observation.psi, observation.threshold,
        not observation.drifted
    )
    invalid = report.__class__(
        report.version, report.feature_version, report.source_artifact_count,
        report.source_feature_names, report.period_days, report.rules,
        report.bin_count, (changed,), report.drifted_features,
        report.drifted_periods, report.drifted, report.report_identity
    )
    assert not validate_feature_drift_report(invalid).is_valid


def test_validation_detects_negative_psi():
    report = build_feature_drift_report(make_source())
    observation = report.observations[0]
    changed = observation.__class__(
        observation.feature_name, observation.baseline_period_start,
        observation.comparison_period_start, observation.baseline_count,
        observation.comparison_count, observation.baseline_missing_rate,
        observation.comparison_missing_rate, observation.baseline_mean,
        observation.comparison_mean, observation.baseline_std,
        observation.comparison_std, -1.0, observation.threshold,
        observation.drifted
    )
    invalid = report.__class__(
        report.version, report.feature_version, report.source_artifact_count,
        report.source_feature_names, report.period_days, report.rules,
        report.bin_count, (changed,), report.drifted_features,
        report.drifted_periods, report.drifted, report.report_identity
    )
    assert not validate_feature_drift_report(invalid).is_valid

def test_validation_detects_wrong_identity_prefix():
    report = build_feature_drift_report(make_source())
    invalid = report.__class__(
        report.version, report.feature_version, report.source_artifact_count,
        report.source_feature_names, report.period_days, report.rules,
        report.bin_count, report.observations, report.drifted_features,
        report.drifted_periods, report.drifted, "bad"
    )
    assert not validate_feature_drift_report(invalid).is_valid


def test_report_preserves_chronological_baseline():
    source = tuple(reversed(make_source()))
    report = build_feature_drift_report(source)
    observation = report.observations[0]
    assert observation.baseline_period_start == date(2026, 1, 1)


def test_missing_calendar_dates_do_not_create_empty_periods():
    source = make_source()
    report = build_feature_drift_report(source)
    assert len(report.observations) == 1


def test_feature_observation_order_is_deterministic():
    report = build_feature_drift_report(
        make_source(second=(9.0, 9.1, 8.9, 9.0))
    )
    observation = report.observations[0]
    assert observation.comparison_period_start > observation.baseline_period_start


def test_summary_contains_identity():
    report = build_feature_drift_report(make_source())
    assert feature_drift_summary(report)["report_identity"] == report.report_identity


def test_validation_returns_invalid_for_non_report():
    result = validate_feature_drift_report(object())
    assert result.status == "INVALID"
    assert result.issues == ("INVALID_REPORT_TYPE",)
