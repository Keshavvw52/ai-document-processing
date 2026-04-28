import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.models.models import Batch, Document
from src.schemas.schemas import BatchUploadResponse, UploadResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED = settings.allowed_extensions_set


def _validate_file(file: UploadFile) -> None:
    ext = Path(file.filename or "").suffix.lstrip(".").lower()
    if ext not in ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type .{ext} not allowed. Allowed: {', '.join(ALLOWED)}",
        )


async def _save_upload(file: UploadFile, dest_dir: Path) -> tuple[str, str, int, str]:
    """Save uploaded file; returns (saved_path, filename, size, mime_type)."""
    ext = Path(file.filename or "unnamed").suffix.lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    dest_path = dest_dir / unique_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    size = 0
    with open(dest_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            size += len(chunk)
            if size > settings.max_file_size_bytes:
                f.close()
                os.remove(dest_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Max: {settings.max_file_size_mb}MB",
                )
            f.write(chunk)

    mime = file.content_type or "application/octet-stream"
    return str(dest_path), unique_name, size, mime


@router.post("", response_model=UploadResponse)
async def upload_single(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a single document for processing."""
    _validate_file(file)
    file_path, filename, size, mime = await _save_upload(file, settings.upload_path)

    doc = Document(
        filename=filename,
        original_filename=file.filename or filename,
        file_path=file_path,
        file_size=size,
        mime_type=mime,
        document_type=document_type,
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info(f"Uploaded document {doc.id}: {doc.original_filename}")
    return UploadResponse(
        document_id=doc.id,
        filename=doc.original_filename,
        status="uploaded",
        message="Document uploaded successfully. Use /api/extract to process it.",
    )


@router.post("/batch", response_model=BatchUploadResponse)
async def upload_batch(
    files: list[UploadFile] = File(...),
    batch_name: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload multiple documents as a batch."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 files per batch")

    # Create batch record
    batch = Batch(
        name=batch_name or f"Batch {len(files)} documents",
        status="pending",
        total_documents=len(files),
    )
    db.add(batch)
    await db.flush()  # get batch.id

    document_ids = []
    for file in files:
        try:
            _validate_file(file)
            file_path, filename, size, mime = await _save_upload(file, settings.upload_path)
            doc = Document(
                filename=filename,
                original_filename=file.filename or filename,
                file_path=file_path,
                file_size=size,
                mime_type=mime,
                document_type=document_type,
                status="uploaded",
                batch_id=batch.id,
            )
            db.add(doc)
            await db.flush()
            document_ids.append(doc.id)
        except HTTPException as e:
            logger.warning(f"Skipping {file.filename}: {e.detail}")
        except Exception as e:
            logger.error(f"Failed to upload {file.filename}: {e}")

    batch.total_documents = len(document_ids)
    await db.commit()

    return BatchUploadResponse(
        batch_id=batch.id,
        document_ids=document_ids,
        total=len(document_ids),
        message=f"Batch created with {len(document_ids)} documents. Use /api/extract/batch to process.",
    )
