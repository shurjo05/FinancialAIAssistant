"""CSV upload endpoints: parse -> categorize -> persist. Plus a sample loader."""

import io
import time
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.metrics import metrics
from app.models.models import Transaction, Upload, User
from app.schemas.schemas import UploadResult
from app.services.categorizer import categorize_batch
from app.services.detector import run_detectors
from app.services.parser import parse_csv

router = APIRouter(prefix="/api", tags=["upload"])

# Bundled sample CSV (repo_root/data/chase_sample.csv) for the demo button.
SAMPLE_CSV = Path(__file__).resolve().parents[3] / "data" / "chase_sample.csv"

# Upload guardrails: bound memory and work per request.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROWS = 10_000


def _ingest(
    db: Session, background_tasks: BackgroundTasks, user_id: int, filename: str, text: str
) -> UploadResult:
    """Shared pipeline: parse -> categorize -> persist -> schedule detectors."""
    started = time.perf_counter()
    rows, errors = parse_csv(io.StringIO(text))
    if not rows and errors:
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse any rows: {errors[0]['issue']}",
        )
    if len(rows) > MAX_ROWS:
        raise HTTPException(
            status_code=413,
            detail=f"Too many rows ({len(rows)}); the maximum is {MAX_ROWS}.",
        )

    dates = [r["date"] for r in rows]
    upload = Upload(
        user_id=user_id,
        filename=filename,
        row_count=len(rows),
        date_range_start=min(dates) if dates else None,
        date_range_end=max(dates) if dates else None,
        status="complete",
    )
    db.add(upload)
    db.flush()  # assigns upload.id without committing yet

    categorized = categorize_batch(
        [r["description"] for r in rows],
        [r["transaction_type"] for r in rows],
    )
    # One batched INSERT instead of N ORM adds. All non-nullable columns are set
    # explicitly (incl. the detector flags) so we don't rely on default timing.
    mappings = [
        {
            "upload_id": upload.id,
            "user_id": user_id,
            "date": r["date"],
            "description": r["description"],
            "merchant_normalized": r["merchant_normalized"],
            "amount": r["amount"],
            "transaction_type": r["transaction_type"],
            "category": category,
            "category_confidence": confidence,
            "is_recurring": False,
            "is_anomaly": False,
        }
        for r, (category, confidence) in zip(rows, categorized, strict=False)
    ]
    if mappings:
        db.bulk_insert_mappings(Transaction, mappings)

    db.commit()
    db.refresh(upload)

    # Observability: ingest latency, volume, and low-confidence rate (feeds the
    # Phase 14 active-learning work). No financial values are recorded.
    metrics.observe_ms("csv_ingest", (time.perf_counter() - started) * 1000)
    metrics.incr("transactions_ingested_total", len(mappings))
    metrics.incr(
        "low_confidence_categorizations",
        sum(1 for _, conf in categorized if conf < 0.5),
    )

    # Detection runs asynchronously so the response returns quickly.
    background_tasks.add_task(run_detectors, upload.id)

    return UploadResult(
        upload_id=upload.id,
        filename=upload.filename,
        row_count=upload.row_count,
        error_count=len(errors),
        date_range_start=upload.date_range_start,
        date_range_end=upload.date_range_end,
        status=upload.status,
        errors=errors,
    )


@router.post("/upload", response_model=UploadResult)
def upload_csv(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadResult:
    """Accept a bank CSV, parse and categorize it, and store the transactions."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    # Bounded read: pull at most the cap + 1 byte so an oversized upload can't
    # exhaust memory, then reject if it exceeded the cap.
    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large; the maximum is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if not raw:
        raise HTTPException(status_code=400, detail="The file is empty.")

    text = raw.decode("utf-8-sig", errors="replace")
    return _ingest(db, background_tasks, user.id, file.filename, text)


@router.post("/load-sample", response_model=UploadResult)
def load_sample(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadResult:
    """Load the bundled sample dataset so the app can be tried without a CSV."""
    if not SAMPLE_CSV.exists():
        raise HTTPException(status_code=404, detail="Sample data file not found.")
    text = SAMPLE_CSV.read_text(encoding="utf-8-sig")
    return _ingest(db, background_tasks, user.id, "sample_transactions.csv", text)
