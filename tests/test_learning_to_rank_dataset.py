from datetime import date, timedelta

import pytest

from analytics.learning_to_rank_dataset import (
    INVALID,
    LEARNING_TO_RANK_DATASET_VERSION,
    SPLIT_TEST,
    SPLIT_TRAIN,
    SPLIT_VALIDATION,
    LearningToRankCandidateInput,
    LearningToRankDatasetConfig,
    LearningToRankObservationInput,
    build_learning_to_rank_dataset,
    get_learning_to_rank_group,
    get_learning_to_rank_split_rows,
    learning_to_rank_group_sizes,
    learning_to_rank_summary,
    validate_learning_to_rank_config,
    validate_learning_to_rank_dataset,
)


def config():
    return LearningToRankDatasetConfig(
        feature_names=("f1", "f2"),
        validation_start_date=date(2026, 1, 11),
        test_start_date=date(2026, 1, 21),
        target_position="close",
    )


def observation(day, group, actual=0, available=None):
    available = available or day - timedelta(days=1)
    candidates = tuple(
        LearningToRankCandidateInput(
            candidate_digit=digit,
            feature_values=(float(digit), float(digit + 1)),
            feature_available_date=available,
            panel_family_id=f"p{digit}",
            jodi_family_id=f"j{digit}",
        )
        for digit in range(10)
    )
    return LearningToRankObservationInput(
        group_id=group,
        target_date=day,
        target_position="close",
        actual_digit=actual,
        candidates=candidates,
        source_observation_identity=f"source-{group}",
    )


def dataset():
    return build_learning_to_rank_dataset(
        (
            observation(date(2026, 1, 1), "g1", 0),
            observation(date(2026, 1, 5), "g2", 4),
            observation(date(2026, 1, 10), "g3", 9),
            observation(date(2026, 1, 12), "g4", 0),
            observation(date(2026, 1, 15), "g5", 7),
            observation(date(2026, 1, 22), "g6", 3),
        ),
        config(),
        "source-dataset-1",
        "feature-schema-1",
    )


def test_version():
    assert LEARNING_TO_RANK_DATASET_VERSION == "40.0.0"


def test_config_validates():
    validate_learning_to_rank_config(config())


def test_config_rejects_duplicate_features():
    with pytest.raises(ValueError, match="unique"):
        validate_learning_to_rank_config(
            LearningToRankDatasetConfig(
                ("f1", "f1"), date(2026, 1, 11), date(2026, 1, 21)
            )
        )


def test_config_rejects_bad_boundaries():
    with pytest.raises(ValueError, match="before"):
        validate_learning_to_rank_config(
            LearningToRankDatasetConfig(
                ("f1",), date(2026, 1, 21), date(2026, 1, 11)
            )
        )


def test_config_rejects_non_10_candidates():
    with pytest.raises(ValueError, match="exactly digits"):
        validate_learning_to_rank_config(
            LearningToRankDatasetConfig(
                ("f1",), date(2026, 1, 11), date(2026, 1, 21),
                candidate_digits=(1, 2)
            )
        )


def test_empty_observations_rejected():
    with pytest.raises(ValueError, match="at least one"):
        build_learning_to_rank_dataset((), config(), "s", "f")


def test_source_identity_required():
    with pytest.raises(ValueError, match="source_dataset_identity"):
        build_learning_to_rank_dataset((observation(date(2026, 1, 1), "g"),), config(), "", "f")


def test_feature_schema_identity_required():
    with pytest.raises(ValueError, match="feature_schema_identity"):
        build_learning_to_rank_dataset((observation(date(2026, 1, 1), "g"),), config(), "s", "")


def test_each_group_has_ten_rows():
    ds = dataset()
    assert len(ds.rows) == 60
    assert all(group.row_end - group.row_start + 1 == 10 for group in ds.groups)


def test_each_group_has_all_digits():
    ds = dataset()
    for group in ds.groups:
        assert [row.candidate_digit for row in ds.rows[group.row_start:group.row_end + 1]] == list(range(10))


def test_zero_is_a_valid_candidate():
    ds = dataset()
    assert ds.rows[0].candidate_digit == 0
    assert ds.rows[0].candidate_id == "close:digit:0"


def test_binary_label_marks_actual_digit():
    ds = dataset()
    group = ds.groups[1]
    labels = [row.relevance_label for row in ds.rows[group.row_start:group.row_end + 1]]
    assert labels.count(1) == 1
    assert labels[4] == 1


def test_candidate_features_are_preserved():
    ds = dataset()
    row = ds.rows[4]
    assert row.feature_names == ("f1", "f2")
    assert row.feature_values == (4.0, 5.0)


def test_panel_jodi_relationship_is_preserved():
    ds = dataset()
    row = ds.rows[3]
    assert row.panel_family_id == "p3"
    assert row.jodi_family_id == "j3"
    assert row.relationship_key == "panel=p3|jodi=j3"


def test_rows_are_chronological():
    ds = dataset()
    assert [group.target_date for group in ds.groups] == sorted(group.target_date for group in ds.groups)


def test_train_validation_test_boundaries():
    ds = dataset()
    assert len(ds.train_group_ids) == 3
    assert len(ds.validation_group_ids) == 2
    assert len(ds.test_group_ids) == 1
    assert all(ds.groups[i].split == SPLIT_TRAIN for i in range(3))
    assert all(group.split == SPLIT_VALIDATION for group in ds.groups[3:5])
    assert ds.groups[5].split == SPLIT_TEST


def test_split_rows_have_consistent_split():
    ds = dataset()
    assert all(row.split == SPLIT_TRAIN for row in get_learning_to_rank_split_rows(ds, SPLIT_TRAIN))
    assert all(row.split == SPLIT_VALIDATION for row in get_learning_to_rank_split_rows(ds, SPLIT_VALIDATION))
    assert all(row.split == SPLIT_TEST for row in get_learning_to_rank_split_rows(ds, SPLIT_TEST))


def test_group_lookup():
    ds = dataset()
    group = get_learning_to_rank_group(ds, "g4")
    assert group.actual_digit == 0
    assert group.split == SPLIT_VALIDATION


def test_missing_group_lookup_rejected():
    with pytest.raises(ValueError, match="not found"):
        get_learning_to_rank_group(dataset(), "missing")


def test_invalid_split_rejected():
    with pytest.raises(ValueError, match="unsupported"):
        get_learning_to_rank_split_rows(dataset(), "unknown")


def test_group_sizes():
    assert learning_to_rank_group_sizes(dataset()) == (3, 2, 1)


def test_summary_contains_contract():
    summary = learning_to_rank_summary(dataset())
    assert summary["status"] == "VALID"
    assert summary["groups"] == 6
    assert summary["rows"] == 60
    assert summary["candidate_count_per_group"] == 10


def test_identity_is_deterministic():
    assert dataset().dataset_identity == dataset().dataset_identity


def test_identity_changes_with_source_identity():
    first = dataset()
    second = build_learning_to_rank_dataset(
        tuple(
            observation(group.target_date, group.group_id, group.actual_digit)
            for group in first.groups
        ),
        config(),
        "different-source",
        "feature-schema-1",
    )
    assert first.dataset_identity != second.dataset_identity


def test_feature_availability_must_precede_target():
    day = date(2026, 1, 1)
    with pytest.raises(ValueError, match="strictly before"):
        build_learning_to_rank_dataset(
            (observation(day, "g", available=day),),
            config(),
            "s",
            "f",
        )


def test_future_feature_availability_is_rejected():
    day = date(2026, 1, 1)
    with pytest.raises(ValueError, match="strictly before"):
        build_learning_to_rank_dataset(
            (observation(day, "g", available=day + timedelta(days=1)),),
            config(),
            "s",
            "f",
        )


def test_duplicate_group_ids_are_rejected():
    item = observation(date(2026, 1, 1), "same")
    with pytest.raises(ValueError, match="unique"):
        build_learning_to_rank_dataset(
            (item, observation(date(2026, 1, 2), "same")),
            config(),
            "s",
            "f",
        )


def test_missing_candidate_is_rejected():
    item = observation(date(2026, 1, 1), "g")
    broken = LearningToRankObservationInput(
        item.group_id, item.target_date, item.target_position, item.actual_digit,
        item.candidates[:-1],
    )
    with pytest.raises(ValueError, match="ten candidates"):
        build_learning_to_rank_dataset((broken,), config(), "s", "f")


def test_duplicate_candidate_is_rejected():
    item = observation(date(2026, 1, 1), "g")
    candidates = item.candidates[:-1] + (item.candidates[8],)
    broken = LearningToRankObservationInput(
        item.group_id, item.target_date, item.target_position, item.actual_digit, candidates
    )
    with pytest.raises(ValueError, match="0 through 9"):
        build_learning_to_rank_dataset((broken,), config(), "s", "f")


def test_target_position_mismatch_is_rejected():
    item = observation(date(2026, 1, 1), "g")
    broken = LearningToRankObservationInput(
        item.group_id, item.target_date, "jodi", item.actual_digit, item.candidates
    )
    with pytest.raises(ValueError, match="target_position"):
        build_learning_to_rank_dataset((broken,), config(), "s", "f")


def test_actual_digit_zero_is_labeled():
    ds = dataset()
    group = get_learning_to_rank_group(ds, "g1")
    assert group.actual_digit == 0
    assert ds.rows[group.row_start].relevance_label == 1


def test_candidate_ids_are_position_scoped():
    ds = dataset()
    assert all(row.candidate_id.startswith("close:digit:") for row in ds.rows)


def test_rows_within_group_are_digit_sorted():
    ds = dataset()
    for group in ds.groups:
        assert [row.candidate_digit for row in ds.rows[group.row_start:group.row_end + 1]] == list(range(10))


def test_group_ids_are_disjoint_across_splits():
    ds = dataset()
    assert not set(ds.train_group_ids) & set(ds.validation_group_ids)
    assert not set(ds.train_group_ids) & set(ds.test_group_ids)
    assert not set(ds.validation_group_ids) & set(ds.test_group_ids)


def test_validation_accepts_built_dataset():
    result = validate_learning_to_rank_dataset(dataset())
    assert result.is_valid
    assert result.status == "VALID"
    assert result.issues == ()


def test_validation_rejects_wrong_type():
    result = validate_learning_to_rank_dataset(object())
    assert result.status == INVALID


def test_validation_rejects_temporal_feature_leakage():
    ds = dataset()
    row = ds.rows[0]
    broken_row = type(row)(
        row.group_id, row.target_date, row.target_position, row.candidate_id,
        row.candidate_digit, row.relevance_label, row.feature_names,
        row.feature_values, row.target_date, row.panel_family_id,
        row.jodi_family_id, row.relationship_key, row.split
    )
    broken = type(ds)(
        ds.version, ds.source_dataset_identity, ds.feature_schema_identity,
        ds.config, (broken_row,) + ds.rows[1:], ds.groups,
        ds.train_group_ids, ds.validation_group_ids, ds.test_group_ids,
        ds.dataset_identity,
    )
    result = validate_learning_to_rank_dataset(broken)
    assert "FEATURE_TEMPORAL_LEAKAGE" in result.issues


def test_validation_rejects_bad_candidate_identity():
    ds = dataset()
    row = ds.rows[0]
    broken_row = type(row)(
        row.group_id, row.target_date, row.target_position, "bad",
        row.candidate_digit, row.relevance_label, row.feature_names,
        row.feature_values, row.feature_available_date, row.panel_family_id,
        row.jodi_family_id, row.relationship_key, row.split
    )
    broken = type(ds)(
        ds.version, ds.source_dataset_identity, ds.feature_schema_identity,
        ds.config, (broken_row,) + ds.rows[1:], ds.groups,
        ds.train_group_ids, ds.validation_group_ids, ds.test_group_ids,
        ds.dataset_identity,
    )
    result = validate_learning_to_rank_dataset(broken)
    assert "CANDIDATE_ID_ERROR" in result.issues


def test_nonfinite_features_are_rejected():
    item = observation(date(2026, 1, 1), "g")
    candidates = list(item.candidates)
    candidates[0] = LearningToRankCandidateInput(
        0, (float("nan"), 1.0), date(2025, 12, 31)
    )
    broken = LearningToRankObservationInput(
        item.group_id, item.target_date, item.target_position,
        item.actual_digit, tuple(candidates)
    )
    with pytest.raises(ValueError, match="finite"):
        build_learning_to_rank_dataset((broken,), config(), "s", "f")


def test_invalid_label_policy_rejected():
    bad = LearningToRankDatasetConfig(
        ("f1",), date(2026, 1, 11), date(2026, 1, 21),
        label_policy="graded"
    )
    with pytest.raises(ValueError, match="unsupported"):
        validate_learning_to_rank_config(bad)


def test_candidate_digit_bool_rejected():
    item = observation(date(2026, 1, 1), "g")
    candidate = LearningToRankCandidateInput(True, (1.0, 2.0), date(2025, 12, 31))
    broken = LearningToRankObservationInput(
        "g", item.target_date, "close", 0, (candidate,) + item.candidates[1:]
    )
    with pytest.raises(TypeError, match="candidate_digit"):
        build_learning_to_rank_dataset((broken,), config(), "s", "f")


def test_feature_vector_length_is_enforced():
    item = observation(date(2026, 1, 1), "g")
    candidates = list(item.candidates)
    candidates[0] = LearningToRankCandidateInput(0, (1.0,), date(2025, 12, 31))
    broken = LearningToRankObservationInput(
        "g", item.target_date, "close", 0, tuple(candidates)
    )
    with pytest.raises(ValueError, match="feature count"):
        build_learning_to_rank_dataset((broken,), config(), "s", "f")


def test_dataset_has_expected_version():
    assert dataset().version == "40.0.0"


def test_dataset_has_feature_schema_identity():
    assert dataset().feature_schema_identity == "feature-schema-1"


def test_dataset_has_source_identity():
    assert dataset().source_dataset_identity == "source-dataset-1"
