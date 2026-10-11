"""
Ingestion service — B4.
Handles structural validation of uploaded CSV, persistence,
and calls core.detect_anomalies to store initial flags.
"""
from __future__ import annotations

import io
import csv
import logging
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import DatasetUploadResponse, RowError
from app.db import repositories as repo

log = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"date", "sku", "units_sold"}
OPTIONAL_COLUMNS = {"on_hand", "promo_flag"}
MAX_ROWS = 100_000


def _parse_date(val: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            continue
    return None


async def ingest_csv(
    db: AsyncSession,
    filename: str,
    content: bytes,
    is_synthetic: bool = False,
) -> DatasetUploadResponse:
    """Parse CSV, validate structure, persist records and detect anomalies."""
    errors: list[RowError] = []
    valid_rows: list[dict] = []
    skus_seen: set[str] = set()

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        return DatasetUploadResponse(
            filename=filename,
            status="rejected",
            rows_ingested=0,
            skus_created=0,
            anomalies_detected=0,
            errors=[RowError(row=0, message="File is empty or not valid CSV")],
        )

    fieldnames_lower = {f.strip().lower() for f in reader.fieldnames}
    missing = REQUIRED_COLUMNS - fieldnames_lower
    if missing:
        return DatasetUploadResponse(
            filename=filename,
            status="rejected",
            rows_ingested=0,
            skus_created=0,
            anomalies_detected=0,
            errors=[RowError(row=0, message=f"Missing required columns: {missing}")],
        )

    # normalise header keys
    has_on_hand = "on_hand" in fieldnames_lower
    has_promo = "promo_flag" in fieldnames_lower

    for row_num, raw in enumerate(reader, start=2):
        if row_num > MAX_ROWS + 2:
            errors.append(RowError(row=row_num, message=f"File exceeds {MAX_ROWS} row limit — truncated"))
            break

        raw_norm = {k.strip().lower(): v.strip() for k, v in raw.items()}

        # --- date ---
        d = _parse_date(raw_norm.get("date", ""))
        if d is None:
            errors.append(RowError(row=row_num, message=f"Unparseable date: {raw_norm.get('date')}"))
            continue

        # --- sku ---
        sku_val = raw_norm.get("sku", "").strip()
        if not sku_val:
            errors.append(RowError(row=row_num, message="Empty SKU"))
            continue

        # --- units_sold ---
        try:
            units = float(raw_norm["units_sold"])
        except (ValueError, KeyError):
            errors.append(RowError(row=row_num, message=f"units_sold not numeric: {raw_norm.get('units_sold')}"))
            continue

        row_dict: dict = {"date": d, "sku": sku_val, "units_sold": units}

        if has_on_hand and raw_norm.get("on_hand", ""):
            try:
                row_dict["on_hand"] = float(raw_norm["on_hand"])
            except ValueError:
                pass  # optional — silently skip

        if has_promo and raw_norm.get("promo_flag", ""):
            try:
                row_dict["promo_flag"] = int(float(raw_norm["promo_flag"]))
            except ValueError:
                pass

        valid_rows.append(row_dict)
        skus_seen.add(sku_val)

    if not valid_rows:
        return DatasetUploadResponse(
            filename=filename,
            status="rejected",
            rows_ingested=0,
            skus_created=0,
            anomalies_detected=0,
            errors=errors,
        )

    # Upsert SKU rows
    skus_created = 0
    for sku_id in skus_seen:
        existing = await repo.get_sku(db, sku_id)
        if existing is None:
            await repo.upsert_sku(db, sku_id, is_synthetic=is_synthetic)
            skus_created += 1

    # Persist sales records
    rows_inserted = await repo.bulk_insert_sales(db, valid_rows)

    # Detect anomalies via core
    anomalies_detected = 0
    try:
        from stocksense_core import detect_anomalies, SalesRecord
        for sku_id in skus_seen:
            records_db = await repo.get_sales_records(db, sku_id)
            core_records = [
                SalesRecord(
                    date=r.date,
                    sku=r.sku,
                    units_sold=r.units_sold,
                    on_hand=r.on_hand,
                    promo_flag=r.promo_flag,
                )
                for r in records_db
            ]
            flags = detect_anomalies(core_records)
            if flags:
                anomaly_rows = [
                    {
                        "sku": sku_id,
                        "date": f.date,
                        "value": f.value,
                        "expected_value": f.expected_value,
                        "robust_z": f.robust_z,
                        "flags_json": __import__("json").dumps(list(f.flags)),
                        "cls": f.cls,
                        "treatment": f.default_treatment,
                        "source": "rule",
                        "status": "open",
                        "rationale": f.rationale,
                    }
                    for f in flags
                ]
                n = await repo.bulk_insert_anomalies(db, anomaly_rows)
                anomalies_detected += n
    except Exception as exc:
        log.warning("Anomaly detection failed during ingestion: %s", exc)

    return DatasetUploadResponse(
        filename=filename,
        status="accepted",
        rows_ingested=rows_inserted,
        skus_created=skus_created,
        anomalies_detected=anomalies_detected,
        errors=errors,
    )
