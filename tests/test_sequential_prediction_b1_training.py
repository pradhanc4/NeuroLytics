from datetime import date, timedelta

from sqlalchemy.orm import sessionmaker

import analytics.sequential_prediction as sequential
from analytics.sequential_prediction import (
    JODI_TARGET_NAMES,
    train_sequential_models,
    predict_jodi_digits,
)
from database.models import HistoricalResult, Market


def test_b1_training_creates_independent_jodi_models(db, tmp_path, monkeypatch):
    model_dir = tmp_path / "models"
    monkeypatch.setattr(sequential, "MODEL_DIR", model_dir)
    test_session_factory = sessionmaker(
        bind=db.get_bind(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr(sequential, "SessionLocal", test_session_factory)

    market = Market(name="B1 Test Market")
    db.add(market)
    db.commit()
    db.refresh(market)

    for index in range(30):
        digit_a = str(index % 10)
        digit_b = str((index * 3) % 10)
        row = HistoricalResult(
            market_id=market.id,
            result_date=date(2025, 1, 1) + timedelta(days=index),
            open_result=f"{index % 10}{(index + 1) % 10}{(index + 2) % 10}",
            jodi_result=f"{digit_a}{digit_b}",
            close_result=f"{(index + 3) % 10}{(index + 4) % 10}{(index + 5) % 10}",
            col1=index % 10,
            col2=(index + 1) % 10,
            col3=(index + 2) % 10,
            col4=(index + 3) % 10,
            col5=(index + 4) % 10,
            col6=(index + 5) % 10,
            col7=(index + 6) % 10,
            col8=(index + 7) % 10,
        )
        db.add(row)

    db.commit()

    result = train_sequential_models()

    assert result["status"] == "COMPLETED"
    assert result["jodi_b1_independent"] is True
    assert result["jodi_prediction_targets"] == list(JODI_TARGET_NAMES)
    assert set(result["metrics"]) == {
        "jodi_first",
        "jodi_second",
        "close_first",
        "close_second",
        "close_third",
    }
    assert (model_dir / "jodi_first.joblib").exists()
    assert (model_dir / "jodi_second.joblib").exists()

    prediction = predict_jodi_digits(
        "789",
        top_k=10,
        market_name="B1 Test Market",
    )

    assert prediction["independent"] is True
    assert len(prediction["jodi_first_candidates"]) == 10
    assert len(prediction["jodi_second_candidates"]) == 10
    assert prediction["operational_top_k"] == [1, 2, 3, 5, 10]
