from datetime import date

import pytest

from database.classification_service import ClassificationService
from database.historical_input_service import HistoricalInputService
from database.models import Market


def create_market(db):
    """Create a test market."""

    market = Market(
        name="Classification Query Test Market"
    )

    db.add(market)
    db.commit()
    db.refresh(market)

    return market


def create_result(
    db,
    market_name,
    result_date,
    open_result,
    jodi_result,
    close_result,
):
    """Create one historical result through the input service."""

    service = HistoricalInputService(db)

    return service.add_historical_result(
        market_name=market_name,
        result_date=result_date,
        open_result=open_result,
        jodi_result=jodi_result,
        close_result=close_result,
    )


def classify_result(
    db,
    historical_result_id,
    version="v1",
):
    """Create one classification."""

    service = ClassificationService(db)

    return service.classify_result(
        historical_result_id=historical_result_id,
        classification_version=version,
    )


def test_get_classification_by_id(db):
    market = create_market(db)

    result = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    classification = classify_result(
        db,
        result.id,
    )

    service = ClassificationService(db)

    found = service.get_classification_by_id(
        classification.id
    )

    assert found is not None
    assert found.id == classification.id


def test_get_classifications_by_version(db):
    market = create_market(db)

    result_1 = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    result_2 = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 2),
        open_result="456",
        jodi_result="12",
        close_result="654",
    )

    classify_result(db, result_1.id, "v1")
    classify_result(db, result_2.id, "v1")
    classify_result(db, result_2.id, "v2")

    service = ClassificationService(db)

    classifications = service.get_classifications_by_version(
        "v1"
    )

    assert len(classifications) == 2

    assert all(
        item.classification_version == "v1"
        for item in classifications
    )


def test_get_classifications_for_result_returns_all_versions(db):
    market = create_market(db)

    result = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    classify_result(db, result.id, "v1")
    classify_result(db, result.id, "v2")

    service = ClassificationService(db)

    classifications = service.get_classifications_for_result(
        result.id
    )

    assert len(classifications) == 2

    assert [
        item.classification_version
        for item in classifications
    ] == ["v1", "v2"]


def test_get_classifications_by_open_class(db):
    market = create_market(db)

    result = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    classification = classify_result(
        db,
        result.id,
    )

    service = ClassificationService(db)

    classifications = (
        service.get_classifications_by_open_class(
            classification.open_class
        )
    )

    assert len(classifications) == 1
    assert classifications[0].id == classification.id


def test_get_classifications_by_jodi_class(db):
    market = create_market(db)

    result = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    classification = classify_result(
        db,
        result.id,
    )

    service = ClassificationService(db)

    classifications = (
        service.get_classifications_by_jodi_class(
            classification.jodi_class
        )
    )

    assert len(classifications) == 1
    assert classifications[0].id == classification.id


def test_get_classifications_by_close_class(db):
    market = create_market(db)

    result = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    classification = classify_result(
        db,
        result.id,
    )

    service = ClassificationService(db)

    classifications = (
        service.get_classifications_by_close_class(
            classification.close_class
        )
    )

    assert len(classifications) == 1
    assert classifications[0].id == classification.id


def test_get_classifications_by_overall_class(db):
    market = create_market(db)

    result = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    classification = classify_result(
        db,
        result.id,
    )

    service = ClassificationService(db)

    classifications = (
        service.get_classifications_by_overall_class(
            classification.overall_class
        )
    )

    assert len(classifications) == 1
    assert classifications[0].id == classification.id


def test_classification_lookup_can_filter_by_version(db):
    market = create_market(db)

    result = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    v1 = classify_result(
        db,
        result.id,
        "v1",
    )

    classify_result(
        db,
        result.id,
        "v2",
    )

    service = ClassificationService(db)

    classifications = (
        service.get_classifications_by_open_class(
            v1.open_class,
            classification_version="v1",
        )
    )

    assert len(classifications) == 1
    assert classifications[0].classification_version == "v1"


def test_get_classifications_by_date_range(db):
    market = create_market(db)

    result_1 = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    result_2 = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 2),
        open_result="456",
        jodi_result="12",
        close_result="654",
    )

    result_3 = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 5),
        open_result="789",
        jodi_result="34",
        close_result="987",
    )

    classify_result(db, result_1.id)
    classify_result(db, result_2.id)
    classify_result(db, result_3.id)

    service = ClassificationService(db)

    classifications = (
        service.get_classifications_by_date_range(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 2),
        )
    )

    assert len(classifications) == 2

    assert [
        item.historical_result.result_date
        for item in classifications
    ] == [
        date(2026, 1, 1),
        date(2026, 1, 2),
    ]


def test_date_range_is_inclusive(db):
    market = create_market(db)

    result = create_result(
        db=db,
        market_name=market.name,
        result_date=date(2026, 1, 10),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    classify_result(db, result.id)

    service = ClassificationService(db)

    classifications = (
        service.get_classifications_by_date_range(
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 10),
        )
    )

    assert len(classifications) == 1


def test_invalid_classification_id_fails(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Classification ID is required",
    ):
        service.get_classification_by_id(None)


def test_invalid_version_fails(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Classification version is required",
    ):
        service.get_classifications_by_version("")


def test_invalid_open_class_fails(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Open classification is required",
    ):
        service.get_classifications_by_open_class("")


def test_invalid_jodi_class_fails(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Jodi classification is required",
    ):
        service.get_classifications_by_jodi_class("")


def test_invalid_close_class_fails(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Close classification is required",
    ):
        service.get_classifications_by_close_class("")


def test_invalid_overall_class_fails(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Overall classification is required",
    ):
        service.get_classifications_by_overall_class("")


def test_missing_start_date_fails(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Start date is required",
    ):
        service.get_classifications_by_date_range(
            start_date=None,
            end_date=date(2026, 1, 1),
        )


def test_missing_end_date_fails(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="End date is required",
    ):
        service.get_classifications_by_date_range(
            start_date=date(2026, 1, 1),
            end_date=None,
        )


def test_invalid_date_range_fails(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Start date cannot be after end date",
    ):
        service.get_classifications_by_date_range(
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 1),
        )