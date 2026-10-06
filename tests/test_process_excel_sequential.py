from datetime import date
from pathlib import Path

from openpyxl import Workbook

from scripts.process_excel_sequential import (
    DEFAULT_SHEET,
    _top_prediction,
    process_excel,
    read_excel_rows,
)


def _workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = DEFAULT_SHEET
    sheet.append(["Date", "Open", "Jodi", "Close"])
    sheet.append([date(2026, 1, 1), 448, "03", 120])
    sheet.append([date(2026, 1, 3), 356, 48, 134])
    workbook.save(path)


def test_read_excel_rows_preserves_date_gaps_and_zero_jodi(tmp_path):
    path = tmp_path / "RawData.xlsx"
    _workbook(path)

    rows = read_excel_rows(path)

    assert len(rows) == 2
    assert rows[0].result_date == date(2026, 1, 1)
    assert rows[0].jodi_result == "03"
    assert rows[1].result_date == date(2026, 1, 3)


def test_top_prediction_uses_top1_jodi_and_all_three_close_digits():
    payload = {
        "jodi_second_candidates": [{"digit": 7, "probability": 0.9}],
        "close_digit_candidates": {
            "first": [{"digit": 1, "probability": 0.8}],
            "second": [{"digit": 2, "probability": 0.7}],
            "third": [{"digit": 3, "probability": 0.6}],
        },
    }

    assert _top_prediction(payload) == ("7", "123")


def test_dry_run_never_writes_database(tmp_path):
    path = tmp_path / "RawData.xlsx"
    checkpoint = tmp_path / "checkpoint.json"
    _workbook(path)

    result = process_excel(path, checkpoint_path=checkpoint, dry_run=True)

    assert result["status"] == "VALID"
    assert result["dry_run"] is True
    assert result["selected_rows"] == 2
    assert not checkpoint.exists()
