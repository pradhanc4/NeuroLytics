from datetime import date, timedelta

import pytest

from analytics.actual_vs_ranked import (
    ActualVsRankedObservation,
    ActualVsRankedReport,
)
from analytics.concept_drift import (
    CONCEPT_DRIFT_VERSION,
    ConceptDriftRule,
    build_concept_drift_report,
    concept_drift_feature_names,
    concept_drift_observations,
    concept_drift_summary,
    validate_concept_drift_report,
)
from features.feature_artifact import FeatureArtifact
from features.feature_schema import FeatureSchema
from features.feature_versioning import FeatureVersionIdentity


def make_sources(values=(1, 2, 3, 4, 1, 2, 3, 4), hits=(1, 1, 0, 0, 0, 0, 1, 1)):
    schema = FeatureSchema(
        "f1", "55-test", "lag", "test", "col1", 1, 1,
        "test", "result_date < target_date", "float"
    )
    identity = FeatureVersionIdentity("55-test", "feature-test", "sha256", "test")
    artifacts = []
    observations = []
    for index, value in enumerate(values):
        target = date(2026, 1, 1) + timedelta(days=index if index < 4 else 14 + index - 4)
        artifacts.append(
            FeatureArtifact(
                target, "55-test", ("f1",), {"f1": value},
                (schema,), identity, "VALID", "CLEAN"
            )
        )
        hit = hits[index]
        rank = 1 if hit else 2
        observations.append(
            ActualVsRankedObservation(
                "panel", f"g{index}", target, "1", rank,
                1.0 / rank, ((1, hit),), "TOP_1" if hit else "TOP_3",
                0.6, 0.6
            )
        )
    report = ActualVsRankedReport(
        "45.0.0", "panel", "top-k-report-test", tuple(observations),
        ((1, sum(hits)), (2, len(hits) - sum(hits))),
        (("TOP_1", sum(hits)), ("TOP_3", len(hits) - sum(hits))),
        ((1, sum(hits) / len(hits)),),
        len(hits), 0, 2.0, 2.0, sum(
            item.reciprocal_rank for item in observations
        ) / len(observations), 0.6, 0.6, "actual-vs-ranked-report-test"
    )
    return tuple(artifacts), report


def test_version_and_defaults():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    assert report.version == CONCEPT_DRIFT_VERSION
    assert report.period_days == 7
    assert report.bin_count == 5


def test_stable_relationship_not_drifted():
    features, outcomes = make_sources(
        hits=(1, 1, 0, 0, 1, 1, 0, 0)
    )
    report = build_concept_drift_report(features, outcomes)
    assert report.drifted is False


def test_relationship_shift_detected():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    assert report.drifted is True
    assert report.drifted_features == ("f1",)


def test_custom_threshold_can_suppress_drift():
    features, outcomes = make_sources(
        hits=(1, 1, 0, 0, 1, 0, 0, 1)
    )
    report = build_concept_drift_report(
        features, outcomes, rules=(ConceptDriftRule("f1", 0.75),)
    )
    assert report.drifted is False


def test_feature_accessor():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    assert concept_drift_feature_names(report) == ("f1",)


def test_observation_accessor():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    observations = concept_drift_observations(report, "f1")
    assert len(observations) == 1
    assert observations[0].baseline_observation_count == 4
    assert observations[0].comparison_observation_count == 4


def test_summary_valid():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    assert concept_drift_summary(report)["status"] == "VALID"


def test_deterministic_identity():
    features, outcomes = make_sources()
    first = build_concept_drift_report(features, outcomes)
    second = build_concept_drift_report(features, outcomes)
    assert first.report_identity == second.report_identity


def test_identity_changes_with_threshold():
    features, outcomes = make_sources()
    first = build_concept_drift_report(features, outcomes)
    second = build_concept_drift_report(
        features, outcomes, rules=(ConceptDriftRule("f1", 0.2),)
    )
    assert first.report_identity != second.report_identity


def test_requires_two_features():
    features, outcomes = make_sources()
    with pytest.raises(ValueError):
        build_concept_drift_report(features[:1], outcomes)


def test_requires_two_periods():
    features, outcomes = make_sources()
    features = tuple(
        FeatureArtifact(
            item.target_date, item.feature_version, item.feature_names,
            item.feature_values, item.schemas, item.version_identity,
            item.validation_status, item.leakage_status
        ) for item in features[:4]
    )
    outcomes = ActualVsRankedReport(
        outcomes.version, outcomes.source_type, outcomes.source_report_identity,
        outcomes.observations[:4], outcomes.rank_distribution,
        outcomes.rank_bucket_counts, outcomes.hit_rates, 4, 0,
        outcomes.mean_actual_rank, outcomes.median_actual_rank,
        outcomes.mean_reciprocal_rank, outcomes.top_probability_mean,
        outcomes.cumulative_probability_mean, outcomes.report_identity
    )
    with pytest.raises(ValueError):
        build_concept_drift_report(features, outcomes)


@pytest.mark.parametrize("period_days", [0, -1, True, 1.5])
def test_invalid_period(period_days):
    features, outcomes = make_sources()
    with pytest.raises(ValueError):
        build_concept_drift_report(features, outcomes, period_days=period_days)


@pytest.mark.parametrize("bins", [0, 1, -2, True, 1.5])
def test_invalid_bins(bins):
    features, outcomes = make_sources()
    with pytest.raises(ValueError):
        build_concept_drift_report(features, outcomes, bin_count=bins)


@pytest.mark.parametrize("threshold", [0, -1, 1.01, float("inf"), float("nan")])
def test_invalid_threshold(threshold):
    features, outcomes = make_sources()
    with pytest.raises(ValueError):
        build_concept_drift_report(
            features, outcomes, rules=(ConceptDriftRule("f1", threshold),)
        )


def test_unknown_feature_rejected():
    features, outcomes = make_sources()
    with pytest.raises(ValueError):
        build_concept_drift_report(
            features, outcomes, rules=(ConceptDriftRule("missing"),)
        )


def test_duplicate_rules_rejected():
    features, outcomes = make_sources()
    with pytest.raises(ValueError):
        build_concept_drift_report(
            features, outcomes,
            rules=(ConceptDriftRule("f1"), ConceptDriftRule("f1"))
        )


def test_duplicate_feature_dates_rejected():
    features, outcomes = make_sources()
    item = features[1]
    duplicate = FeatureArtifact(
        features[0].target_date, item.feature_version, item.feature_names,
        item.feature_values, item.schemas, item.version_identity, "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_concept_drift_report((features[0], duplicate) + features[2:], outcomes)


def test_mismatched_feature_versions_rejected():
    features, outcomes = make_sources()
    item = features[1]
    changed = FeatureArtifact(
        item.target_date, "other", item.feature_names, item.feature_values,
        item.schemas, item.version_identity, "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_concept_drift_report((features[0], changed) + features[2:], outcomes)


def test_mismatched_feature_names_rejected():
    features, outcomes = make_sources()
    item = features[1]
    schema = FeatureSchema(
        "other", "55-test", "lag", "test", "col1", 1, 1,
        "other", "result_date < target_date", "float"
    )
    changed = FeatureArtifact(
        item.target_date, "55-test", ("other",), {"other": 1.0},
        (schema,), item.version_identity, "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_concept_drift_report((features[0], changed) + features[2:], outcomes)


def test_invalid_feature_artifact_rejected():
    features, outcomes = make_sources()
    item = features[0]
    changed = FeatureArtifact(
        item.target_date, item.feature_version, item.feature_names,
        item.feature_values, item.schemas, item.version_identity, "INVALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_concept_drift_report((changed,) + features[1:], outcomes)


def test_leakage_feature_artifact_rejected():
    features, outcomes = make_sources()
    item = features[0]
    changed = FeatureArtifact(
        item.target_date, item.feature_version, item.feature_names,
        item.feature_values, item.schemas, item.version_identity, "VALID", "LEAKAGE"
    )
    with pytest.raises(ValueError):
        build_concept_drift_report((changed,) + features[1:], outcomes)


def test_outcome_date_mismatch_rejected():
    features, outcomes = make_sources()
    extra = outcomes.observations[0]
    shifted = extra.__class__(
        extra.source_type, extra.group_id, extra.target_date + timedelta(days=1),
        extra.actual_value, extra.actual_rank, extra.reciprocal_rank,
        extra.hit_at_k, extra.rank_bucket, extra.top_probability,
        extra.cumulative_probability_at_max_k
    )
    obs = (shifted,) + outcomes.observations[1:]
    bad = ActualVsRankedReport(
        outcomes.version, outcomes.source_type, outcomes.source_report_identity,
        obs, outcomes.rank_distribution, outcomes.rank_bucket_counts,
        outcomes.hit_rates, outcomes.actual_available_observations,
        outcomes.missed_observations, outcomes.mean_actual_rank,
        outcomes.median_actual_rank, outcomes.mean_reciprocal_rank,
        outcomes.top_probability_mean, outcomes.cumulative_probability_mean,
        outcomes.report_identity
    )
    with pytest.raises(ValueError):
        build_concept_drift_report(features, bad)


def test_invalid_outcome_report_rejected():
    features, outcomes = make_sources()
    bad = ActualVsRankedReport(
        "bad", outcomes.source_type, outcomes.source_report_identity,
        outcomes.observations, outcomes.rank_distribution,
        outcomes.rank_bucket_counts, outcomes.hit_rates,
        outcomes.actual_available_observations, outcomes.missed_observations,
        outcomes.mean_actual_rank, outcomes.median_actual_rank,
        outcomes.mean_reciprocal_rank, outcomes.top_probability_mean,
        outcomes.cumulative_probability_mean, outcomes.report_identity
    )
    with pytest.raises(ValueError):
        build_concept_drift_report(features, bad)


def test_missing_outcome_is_excluded():
    features, outcomes = make_sources()
    item = outcomes.observations[0]
    missing = item.__class__(
        item.source_type, item.group_id, item.target_date, None, None,
        0.0, ((1, False),), "UNAVAILABLE", item.top_probability,
        item.cumulative_probability_at_max_k
    )
    observations = (missing,) + outcomes.observations[1:]
    bad = ActualVsRankedReport(
        outcomes.version, outcomes.source_type, outcomes.source_report_identity,
        observations, outcomes.rank_distribution, outcomes.rank_bucket_counts,
        outcomes.hit_rates, 7, 1, outcomes.mean_actual_rank,
        outcomes.median_actual_rank, outcomes.mean_reciprocal_rank,
        outcomes.top_probability_mean, outcomes.cumulative_probability_mean,
        outcomes.report_identity
    )
    report = build_concept_drift_report(features, bad)
    assert report.drifted is True


def test_zero_feature_values_supported():
    features, outcomes = make_sources(values=(0, 0, 1, 1, 0, 0, 1, 1))
    report = build_concept_drift_report(features, outcomes)
    assert validate_concept_drift_report(report).is_valid


def test_constant_feature_relationship_supported():
    features, outcomes = make_sources(values=(1, 1, 1, 1, 1, 1, 1, 1))
    report = build_concept_drift_report(features, outcomes)
    assert report.observations[0].conditional_rate_change == 0.0


def test_non_numeric_feature_value_rejected():
    features, outcomes = make_sources()
    item = features[-1]
    changed = FeatureArtifact(
        item.target_date, item.feature_version, item.feature_names,
        {"f1": "bad"}, item.schemas, item.version_identity, "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_concept_drift_report(features[:-1] + (changed,), outcomes)


def test_boolean_feature_value_rejected():
    features, outcomes = make_sources()
    item = features[-1]
    changed = FeatureArtifact(
        item.target_date, item.feature_version, item.feature_names,
        {"f1": True}, item.schemas, item.version_identity, "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_concept_drift_report(features[:-1] + (changed,), outcomes)


def test_nan_feature_value_rejected():
    features, outcomes = make_sources()
    item = features[-1]
    changed = FeatureArtifact(
        item.target_date, item.feature_version, item.feature_names,
        {"f1": float("nan")}, item.schemas, item.version_identity, "VALID", "CLEAN"
    )
    with pytest.raises(ValueError):
        build_concept_drift_report(features[:-1] + (changed,), outcomes)


def test_no_paired_numeric_period_rejected():
    features, outcomes = make_sources()
    changed = tuple(
        FeatureArtifact(
            item.target_date, item.feature_version, item.feature_names,
            {"f1": None}, item.schemas, item.version_identity, "VALID", "CLEAN"
        ) for item in features[4:]
    )
    with pytest.raises(ValueError):
        build_concept_drift_report(features[:4] + changed, outcomes)


def test_feature_names_order_preserved():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    assert report.rules[0].feature_name == "f1"


def test_baseline_is_earliest_period():
    features, outcomes = make_sources()
    report = build_concept_drift_report(tuple(reversed(features)), outcomes)
    assert report.observations[0].baseline_period_start == date(2026, 1, 1)


def test_missing_calendar_dates_are_not_fabricated():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    assert len(report.observations) == 1


def test_threshold_is_inclusive():
    features, outcomes = make_sources()
    base = build_concept_drift_report(features, outcomes)
    change = base.observations[0].conditional_rate_change
    report = build_concept_drift_report(
        features, outcomes, rules=(ConceptDriftRule("f1", change),)
    )
    assert report.drifted is True


def test_report_validation_passes():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    assert validate_concept_drift_report(report).is_valid


def test_validation_detects_bad_version():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    bad = report.__class__(
        "bad", report.source_type, report.feature_version,
        report.source_feature_artifact_count,
        report.source_outcome_report_identity, report.period_days,
        report.bin_count, report.rules, report.observations,
        report.drifted_features, report.drifted_periods,
        report.drifted, report.report_identity
    )
    assert not validate_concept_drift_report(bad).is_valid


def test_validation_detects_bad_flag():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    bad = report.__class__(
        report.version, report.source_type, report.feature_version,
        report.source_feature_artifact_count, report.source_outcome_report_identity,
        report.period_days, report.bin_count, report.rules, report.observations,
        report.drifted_features, report.drifted_periods, not report.drifted,
        report.report_identity
    )
    assert not validate_concept_drift_report(bad).is_valid


def test_validation_detects_bad_change():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    item = report.observations[0]
    changed = item.__class__(
        item.feature_name, item.baseline_period_start, item.comparison_period_start,
        item.baseline_observation_count, item.comparison_observation_count,
        item.baseline_outcome_rate, item.comparison_outcome_rate, -1.0,
        item.threshold, item.drifted
    )
    bad = report.__class__(
        report.version, report.source_type, report.feature_version,
        report.source_feature_artifact_count, report.source_outcome_report_identity,
        report.period_days, report.bin_count, report.rules, (changed,),
        report.drifted_features, report.drifted_periods, report.drifted,
        report.report_identity
    )
    assert not validate_concept_drift_report(bad).is_valid


def test_validation_detects_bad_identity():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    bad = report.__class__(
        report.version, report.source_type, report.feature_version,
        report.source_feature_artifact_count, report.source_outcome_report_identity,
        report.period_days, report.bin_count, report.rules, report.observations,
        report.drifted_features, report.drifted_periods, report.drifted, "bad"
    )
    assert not validate_concept_drift_report(bad).is_valid


def test_validation_rejects_invalid_type():
    assert validate_concept_drift_report(object()).issues == ("INVALID_REPORT_TYPE",)


def test_panel_and_jodi_source_boundary():
    features, outcomes = make_sources()
    jodi = ActualVsRankedReport(
        outcomes.version, "jodi", outcomes.source_report_identity,
        outcomes.observations, outcomes.rank_distribution,
        outcomes.rank_bucket_counts, outcomes.hit_rates,
        outcomes.actual_available_observations, outcomes.missed_observations,
        outcomes.mean_actual_rank, outcomes.median_actual_rank,
        outcomes.mean_reciprocal_rank, outcomes.top_probability_mean,
        outcomes.cumulative_probability_mean, outcomes.report_identity
    )
    report = build_concept_drift_report(features, jodi)
    assert report.source_type == "jodi"


def test_outcome_identity_is_preserved():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    assert report.source_outcome_report_identity == outcomes.report_identity


def test_feature_version_is_preserved():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    assert report.feature_version == "55-test"


def test_summary_identity():
    features, outcomes = make_sources()
    report = build_concept_drift_report(features, outcomes)
    assert concept_drift_summary(report)["report_identity"] == report.report_identity


def test_multi_feature_monitoring():
    features, outcomes = make_sources()
    schema2 = FeatureSchema(
        "f2", "55-test", "lag", "test", "col2", 1, 1,
        "test2", "result_date < target_date", "float"
    )
    features2 = tuple(
        FeatureArtifact(
            item.target_date, item.feature_version, ("f1", "f2"),
            {"f1": item.feature_values["f1"], "f2": 1.0},
            (item.schemas[0], schema2), item.version_identity,
            "VALID", "CLEAN"
        ) for item in features
    )
    report = build_concept_drift_report(features2, outcomes)
    assert len(report.rules) == 2
    assert report.drifted_features == ("f1",)


def test_explicit_rule_can_select_schema_declared_string():
    features, outcomes = make_sources()
    schema = FeatureSchema(
        "f1", "55-test", "lag", "test", "col1", 1, 1,
        "test", "result_date < target_date", "string"
    )
    features = tuple(
        FeatureArtifact(
            item.target_date, item.feature_version, item.feature_names,
            item.feature_values, (schema,), item.version_identity,
            "VALID", "CLEAN"
        ) for item in features
    )
    report = build_concept_drift_report(
        features, outcomes, rules=(ConceptDriftRule("f1"),)
    )
    assert validate_concept_drift_report(report).is_valid


def test_default_non_numeric_feature_is_not_selected():
    features, outcomes = make_sources()
    schema = FeatureSchema(
        "f1", "55-test", "lag", "test", "col1", 1, 1,
        "test", "result_date < target_date", "string"
    )
    features = tuple(
        FeatureArtifact(
            item.target_date, item.feature_version, item.feature_names,
            item.feature_values, (schema,), item.version_identity,
            "VALID", "CLEAN"
        ) for item in features
    )
    with pytest.raises(ValueError):
        build_concept_drift_report(features, outcomes)
