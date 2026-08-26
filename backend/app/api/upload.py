"""CSV upload endpoint: parse -> categorize -> persist."""

import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Transaction, Upload
from app.schemas.schemas import UploadResult
from app.services.categorizer import categorize
from app.services.parser import parse_csv

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResult)
def upload_csv(file: UploadFile, db: Session = Depends(get_db)) -> UploadResult:
    """Accept a bank CSV, parse and categorize it, and store the transactions."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    # Decode bytes to text; utf-8-sig strips a BOM if present.
    raw_bytes = file.file.read()
    text = raw_bytes.decode("utf-8-sig", errors="replace")

    rows, errors = parse_csv(io.StringIO(text))
    if not rows and errors:
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse any rows: {errors[0]['issue']}",
        )

    # Create the upload record first so transactions can reference its id.
    dates = [r["date"] for r in rows]
    upload = Upload(
        filename=file.filename,
        row_count=len(rows),
        date_range_start=min(dates) if dates else None,
        date_range_end=max(dates) if dates else None,
        status="complete",
    )
    db.add(upload)
    db.flush()  # assigns upload.id without committing yet

    for r in rows:
        category, confidence = categorize(r["description"])
        db.add(Transaction(
            upload_id=upload.id,
            date=r["date"],
            description=r["description"],
            merchant_normalized=r["merchant_normalized"],
            amount=r["amount"],
            transaction_type=r["transaction_type"],
            category=category,
            category_confidence=confidence,
        ))

    db.commit()
    db.refresh(upload)

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
