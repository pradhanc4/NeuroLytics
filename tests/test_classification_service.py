from datetime import date

import pytest

from database.classification_service import (
    ClassificationService,
)
from database.models import (
    HistoricalClassification,
    HistoricalResult,
    Market,
)


def create_market(db):
    """Create a test market."""

    market = Market(
        name="Classification Test Market",
    )

    db.add(market)
    db.commit()
    db.refresh(market)

    return market


def create_historical_result(
    db,
    market,
    result_date,
    open_result,
    jodi_result,
    close_result,
):
    """Create a test historical result."""

    historical_result = HistoricalResult(
        market_id=market.id,
        result_date=result_date,
        open_result=open_result,
        jodi_result=jodi_result,
        close_result=close_result,
        col1=int(open_result[0]),
        col2=int(open_result[1]),
        col3=int(open_result[2]),
        col4=int(jodi_result[0]),
        col5=int(jodi_result[1]),
        col6=int(close_result[0]),
        col7=int(close_result[1]),
        col8=int(close_result[2]),
    )

    db.add(historical_result)
    db.commit()
    db.refresh(historical_result)

    return historical_result


def test_classify_result_creates_sql_record(db):
    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 1, 1),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    service = ClassificationService(db)

    classification = service.classify_result(
        historical_result_id=historical_result.id,
        classification_version="v1",
    )

    assert classification.id is not None
    assert classification.historical_result_id == (
        historical_result.id
    )
    assert classification.classification_version == "v1"

    assert classification.open_class == (
        "TRIPLE_UNIQUE|NO_ZERO|LOW_SUM|OEO|ASCENDING"
    )

    assert classification.jodi_class == (
        "NON_DOUBLE|DIFFERENT_DIGIT|EO"
    )

    assert classification.close_class == (
        "TRIPLE_UNIQUE|NO_ZERO|LOW_SUM|OEO|DESCENDING"
    )

    assert classification.overall_class == (
        "REVERSED|3_MATCH"
    )


def test_classification_is_persisted_in_sql(db):
    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 1, 2),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    service = ClassificationService(db)

    classification = service.classify_result(
        historical_result_id=historical_result.id,
    )

    stored = db.get(
        HistoricalClassification,
        classification.id,
    )

    assert stored is not None
    assert stored.id == classification.id
    assert stored.historical_result_id == (
        historical_result.id
    )


def test_get_classification(db):
    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 1, 3),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    service = ClassificationService(db)

    created = service.classify_result(
        historical_result_id=historical_result.id,
        classification_version="v1",
    )

    retrieved = service.get_classification(
        historical_result_id=historical_result.id,
        classification_version="v1",
    )

    assert retrieved is not None
    assert retrieved.id == created.id


def test_duplicate_classification_is_not_created(db):
    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 1, 4),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    service = ClassificationService(db)

    first = service.classify_result(
        historical_result_id=historical_result.id,
        classification_version="v1",
    )

    second = service.classify_result(
        historical_result_id=historical_result.id,
        classification_version="v1",
    )

    assert first.id == second.id

    classifications = (
        db.query(HistoricalClassification)
        .filter(
            HistoricalClassification.historical_result_id
            == historical_result.id
        )
        .all()
    )

    assert len(classifications) == 1


def test_different_versions_can_coexist(db):
    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 1, 5),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    service = ClassificationService(db)

    version_one = service.classify_result(
        historical_result_id=historical_result.id,
        classification_version="v1",
    )

    version_two = service.classify_result(
        historical_result_id=historical_result.id,
        classification_version="v2",
    )

    assert version_one.id != version_two.id

    assert version_one.classification_version == "v1"
    assert version_two.classification_version == "v2"

    classifications = (
        db.query(HistoricalClassification)
        .filter(
            HistoricalClassification.historical_result_id
            == historical_result.id
        )
        .all()
    )

    assert len(classifications) == 2


def test_missing_historical_result_raises_error(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Historical result not found",
    ):
        service.classify_result(
            historical_result_id=999999,
        )


def test_missing_result_id_raises_error(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Historical result ID is required",
    ):
        service.classify_result(
            historical_result_id=None,
        )


def test_missing_version_raises_error(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Classification version is required",
    ):
        service.classify_result(
            historical_result_id=1,
            classification_version="",
        )


def test_classify_multiple_results(db):
    market = create_market(db)

    result_one = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 1, 6),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    result_two = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 1, 7),
        open_result="111",
        jodi_result="22",
        close_result="999",
    )

    service = ClassificationService(db)

    classifications = service.classify_results(
        historical_result_ids=[
            result_one.id,
            result_two.id,
        ],
        classification_version="v1",
    )

    assert len(classifications) == 2

    assert (
        classifications[0].historical_result_id
        == result_one.id
    )

    assert (
        classifications[1].historical_result_id
        == result_two.id
    )


def test_empty_result_list_raises_error(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="At least one historical result ID is required",
    ):
        service.classify_results(
            historical_result_ids=[],
        )


def test_get_all_classifications_for_result(db):
    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 1, 8),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    service = ClassificationService(db)

    service.classify_result(
        historical_result_id=historical_result.id,
        classification_version="v1",
    )

    service.classify_result(
        historical_result_id=historical_result.id,
        classification_version="v2",
    )

    classifications = (
        service.get_classifications_for_result(
            historical_result_id=historical_result.id,
        )
    )

    assert len(classifications) == 2

    versions = [
        classification.classification_version
        for classification in classifications
    ]

    assert versions == ["v1", "v2"]


def test_get_classification_returns_none_when_missing(db):
    market = create_market(db)

    historical_result = create_historical_result(
        db=db,
        market=market,
        result_date=date(2026, 1, 9),
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    service = ClassificationService(db)

    result = service.get_classification(
        historical_result_id=historical_result.id,
        classification_version="v99",
    )

    assert result is None


def test_get_classifications_requires_result_id(db):
    service = ClassificationService(db)

    with pytest.raises(
        ValueError,
        match="Historical result ID is required",
    ):
        service.get_classifications_for_result(
            historical_result_id=None,
        )