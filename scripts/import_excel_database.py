"""Deterministic Excel -> database importer for NeuroLytics.

This importer has ONE responsibility: load validated historical rows into the
database in Excel/date order. It intentionally does not load, train, predict,
evaluate, rank, or retrain any ML model.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from analytics.live_activity import live_activity
from database.engine import SessionLocal
from database.models import HistoricalResult, Market
from database.parser import parse_results

DEFAULT_EXCEL = ROOT_DIR / "data" / "RawData.xlsx"
DEFAULT_SHEET = "Open Jodi Close"
DEFAULT_MARKET = "Excel Sequential Market"
DEFAULT_CHECKPOINT = ROOT_DIR / "data" / "excel_import_checkpoint.json"


@dataclass(frozen=True)
class ExcelImportRow:
    row_number: int
    result_date: date
    open_result: str
    jodi_result: str
    close_result: str


def _digits(value: Any, width: int, label: str) -> str:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{label}: missing/invalid value")
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if not text.isdigit() or len(text) > width:
        raise ValueError(f"{label}: expected at most {width} digits, got {text!r}")
    return text.zfill(width)


def _date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00")).date()


def read_excel_rows(path: Path, sheet_name: str = DEFAULT_SHEET) -> list[ExcelImportRow]:
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet_name not in workbook.sheetnames:
            raise ValueError(f"Worksheet not found: {sheet_name!r}")
        sheet = workbook[sheet_name]
        result: list[ExcelImportRow] = []
        seen: set[date] = set()
        previous: date | None = None
        for row_number, values in enumerate(
            sheet.iter_rows(min_row=2, values_only=True), start=2
        ):
            if not any(value is not None for value in values):
                continue
            if len(values) < 4:
                raise ValueError(f"row {row_number}: expected Date/Open/Jodi/Close")
            result_date = _date(values[0])
            if result_date in seen:
                raise ValueError(f"row {row_number}: duplicate date {result_date}")
            if previous is not None and result_date <= previous:
                raise ValueError(f"row {row_number}: dates are not strictly increasing")
            seen.add(result_date)
            previous = result_date
            result.append(
                ExcelImportRow(
                    row_number=row_number,
                    result_date=result_date,
                    open_result=_digits(values[1], 3, "Open"),
                    jodi_result=_digits(values[2], 2, "Jodi"),
                    close_result=_digits(values[3], 3, "Close"),
                )
            )
        if not result:
            raise ValueError("worksheet contains no data rows")
        return result
    finally:
        workbook.close()


def _load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "version": 1,
            "source": None,
            "market": None,
            "last_row_number": 1,
            "last_date": None,
            "processed": 0,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def _save_checkpoint(
    path: Path,
    *,
    source: str,
    market: str,
    row: ExcelImportRow,
    processed: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "source": source,
        "market": market,
        "last_row_number": row.row_number,
        "last_date": row.result_date.isoformat(),
        "processed": processed,
        "updated_at": datetime.now().astimezone().isoformat(),
    }
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def _market(market_name: str) -> Market:
    db = SessionLocal()
    try:
        market = db.scalar(select(Market).where(Market.name == market_name))
        if market is None:
            market = Market(name=market_name)
            db.add(market)
            db.commit()
            db.refresh(market)
        return market
    finally:
        db.close()


def _stored_dates(market_name: str) -> set[date]:
    db = SessionLocal()
    try:
        market = db.scalar(select(Market).where(Market.name == market_name))
        if market is None:
            return set()
        return set(
            db.scalars(
                select(HistoricalResult.result_date).where(
                    HistoricalResult.market_id == market.id
                )
            ).all()
        )
    finally:
        db.close()


def import_excel(
    excel_path: Path = DEFAULT_EXCEL,
    *,
    market_name: str = DEFAULT_MARKET,
    checkpoint_path: Path = DEFAULT_CHECKPOINT,
    sheet_name: str = DEFAULT_SHEET,
    start_row: int | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    rows = read_excel_rows(excel_path, sheet_name)
    source = str(excel_path.resolve())
    checkpoint = _load_checkpoint(checkpoint_path)

    if checkpoint.get("source") not in (None, source):
        raise ValueError("checkpoint belongs to a different Excel source")
    if checkpoint.get("market") not in (None, market_name):
        raise ValueError("checkpoint belongs to a different market")

    checkpoint_row = int(checkpoint.get("last_row_number", 1))
    stored_dates = _stored_dates(market_name)
    if start_row is None and not checkpoint.get("source") and stored_dates:
        excel_dates = [row.result_date for row in rows]
        max_stored = max(stored_dates)
        try:
            prefix_end = excel_dates.index(max_stored)
        except ValueError as exc:
            raise ValueError(
                "database contains a date that is not present in the selected Excel source"
            ) from exc
        expected_prefix = set(excel_dates[: prefix_end + 1])
        if stored_dates != expected_prefix:
            raise ValueError(
                "existing database rows are not a contiguous Excel prefix; "
                "refusing to guess the resume position"
            )
        checkpoint_row = rows[prefix_end].row_number
        first_row = checkpoint_row + 1
        checkpoint["processed"] = prefix_end + 1
        checkpoint["last_row_number"] = checkpoint_row
        checkpoint["last_date"] = rows[prefix_end].result_date.isoformat()
    else:
        first_row = start_row if start_row is not None else checkpoint_row + 1
    selected = [row for row in rows if row.row_number >= first_row]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        selected = selected[:limit]

    if dry_run:
        live_activity.reset(source="EXCEL_DATABASE_IMPORT")
        live_activity.set_status("READY", "Excel validation completed; no database writes made")
        return {
            "status": "VALID",
            "dry_run": True,
            "source": source,
            "total_rows": len(rows),
            "selected_rows": len(selected),
            "first_row": selected[0].row_number if selected else None,
            "last_row": selected[-1].row_number if selected else None,
        }

    live_activity.reset(source="EXCEL_DATABASE_IMPORT")
    live_activity.emit(
        "Excel database import started",
        status="RUNNING",
        source="EXCEL_DATABASE_IMPORT",
        stage="DATABASE_IMPORT",
        operation="Validating and storing Excel rows one at a time",
        processed_entries=int(checkpoint.get("processed", 0)),
    )

    market = _market(market_name)
    stored = _stored_dates(market_name)
    processed = int(checkpoint.get("processed", 0))
    imported = 0
    skipped_existing = 0

    for index, row in enumerate(selected, start=1):
        live_activity.emit(
            "Reading Excel row",
            status="RUNNING",
            source="EXCEL_DATABASE_IMPORT",
            current_date=row.result_date.isoformat(),
            stage="DATABASE_IMPORT",
            operation=f"Reading Excel row {row.row_number}",
            processed_entries=processed,
            total_entries=len(rows),
        )

        if row.result_date in stored:
            # A date already present is only acceptable when it is exactly the
            # checkpoint resume boundary. Any other duplicate is unsafe.
            if row.row_number <= checkpoint_row:
                skipped_existing += 1
                continue
            raise ValueError(
                f"row {row.row_number} ({row.result_date}) already exists; "
                "refusing to silently overwrite or skip it"
            )

        parsed = parse_results(
            open_result=row.open_result,
            jodi_result=row.jodi_result,
            close_result=row.close_result,
        )
        db = SessionLocal()
        try:
            db_market = db.scalar(select(Market).where(Market.name == market_name))
            if db_market is None:
                raise ValueError("market disappeared during import")
            existing = db.scalar(
                select(HistoricalResult).where(
                    HistoricalResult.market_id == db_market.id,
                    HistoricalResult.result_date == row.result_date,
                )
            )
            if existing is not None:
                raise ValueError(
                    f"row {row.row_number} ({row.result_date}) already exists"
                )
            result = HistoricalResult(
                market_id=db_market.id,
                result_date=row.result_date,
                **parsed,
            )
            db.add(result)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        stored.add(row.result_date)
        processed += 1
        imported += 1
        _save_checkpoint(
            checkpoint_path,
            source=source,
            market=market_name,
            row=row,
            processed=processed,
        )
        live_activity.emit(
            "Excel row stored in database",
            status="RUNNING",
            source="EXCEL_DATABASE_IMPORT",
            current_date=row.result_date.isoformat(),
            stage="DATABASE_IMPORT",
            operation=f"Committed database record for Excel row {row.row_number}",
            actual=f"{row.open_result} {row.jodi_result} {row.close_result}",
            processed_entries=processed,
            total_entries=len(rows),
        )

    live_activity.set_status(
        "COMPLETED",
        f"Database import completed: {imported} new records stored",
    )
    live_activity.emit(
        "Excel database import completed",
        status="COMPLETED",
        source="EXCEL_DATABASE_IMPORT",
        stage="DATABASE_IMPORT",
        operation="Excel import finished; ML was not executed",
        processed_entries=processed,
        total_entries=len(rows),
    )
    return {
        "status": "COMPLETED",
        "source": source,
        "market": market_name,
        "total_rows": len(rows),
        "selected_rows": len(selected),
        "imported": imported,
        "skipped_existing": skipped_existing,
        "processed": processed,
        "ml_executed": False,
        "predictions_executed": False,
        "feedback_executed": False,
        "retraining_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Excel historical data into NeuroLytics database only")
    parser.add_argument("--excel", type=Path, default=DEFAULT_EXCEL)
    parser.add_argument("--market", default=DEFAULT_MARKET)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--sheet", default=DEFAULT_SHEET)
    parser.add_argument("--start-row", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = import_excel(
        args.excel,
        market_name=args.market,
        checkpoint_path=args.checkpoint,
        sheet_name=args.sheet,
        start_row=args.start_row,
        limit=args.limit,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
