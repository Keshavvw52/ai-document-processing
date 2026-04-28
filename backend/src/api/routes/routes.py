import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from src.core.database import AsyncSessionLocal, get_db
from src.models.models import Document, ExtractionResult, Batch
from src.schemas.schemas import (
    ClassifyRequest, ClassifyResponse,
    ExtractRequest, BatchExtractRequest,
    FieldUpdateRequest, StatusUpdateRequest,
    ExportRequest, HealthResponse,
)
from src.services.groq_vision import GroqVisionService
from src.services.document_processor import DocumentProcessor
from src.services.export_service import ExportService

logger = logging.getLogger(__name__)

classify_router = APIRouter(prefix="/api", tags=["classify"])
extract_router = APIRouter(prefix="/api", tags=["extract"])
documents_router = APIRouter(prefix="/api/documents", tags=["documents"])
batch_router = APIRouter(prefix="/api/batch", tags=["batch"])
export_router = APIRouter(prefix="/api", tags=["export"])
stats_router = APIRouter(prefix="/api", tags=["stats"])
health_router = APIRouter(prefix="/api", tags=["health"])
templates_router = APIRouter(prefix="/api", tags=["templates"])


def _doc_to_dict(doc: Document) -> dict:
    result = None
    if doc.extraction_result:
        r = doc.extraction_result
        result = {
            "id": r.id,
            "document_id": r.document_id,
            "fields": r.fields,
            "corrected_fields": r.corrected_fields,
            "confidence_scores": r.confidence_scores,
            "bounding_boxes": r.bounding_boxes,
            "tables": r.tables,
            "overall_confidence": r.overall_confidence,
            "summary": r.summary,
            "ocr_engine": r.ocr_engine,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
    pages = [
        {
            "id": p.id,
            "page_number": p.page_number,
            "ocr_text": p.ocr_text,
            "extracted_data": p.extracted_data,
            "bounding_boxes": p.bounding_boxes,
        }
        for p in (doc.pages or [])
    ]
    return {
        "id": doc.id,
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "page_count": doc.page_count,
        "document_type": doc.document_type,
        "classification_confidence": doc.classification_confidence,
        "status": doc.status,
        "error_message": doc.error_message,
        "language_detected": doc.language_detected,
        "batch_id": doc.batch_id,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
        "processed_at": doc.processed_at,
        "extraction_result": result,
        "pages": pages,
    }


# ────────────────────────── Classify ────────────────────────────────────────

@classify_router.post("/classify", response_model=ClassifyResponse)
async def classify_document(
    req: ClassifyRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).where(Document.id == req.document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    groq = GroqVisionService()
    classify_result = groq.classify_document(doc.file_path)

    doc.document_type = classify_result.get("document_type", "form")
    doc.classification_confidence = classify_result.get("confidence", 0.5)
    await db.commit()

    return ClassifyResponse(
        document_id=doc.id,
        document_type=doc.document_type,
        confidence=doc.classification_confidence,
        all_scores=classify_result.get("all_scores"),
    )


# ────────────────────────── Extract ─────────────────────────────────────────

@extract_router.post("/extract")
async def extract_document(
    req: ExtractRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).where(Document.id == req.document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    processor = DocumentProcessor()
    # Run synchronously (for now; Celery handles async batch)
    try:
        extraction_result = await processor.process_document(
            req.document_id,
            db,
            document_type_override=req.document_type,
            force_reprocess=req.force_reprocess,
        )
    except Exception as e:
        logger.exception("Extraction failed for document %s", req.document_id)
        raise HTTPException(
            status_code=500,
            detail="Document extraction failed. Please try again later.",
        ) from e

    return {"message": "Extraction complete", **extraction_result}


@extract_router.post("/extract/batch")
async def extract_batch(
    req: BatchExtractRequest,
    background_tasks: BackgroundTasks,
):
    async def _process_all():
        async with AsyncSessionLocal() as session:
            processor = DocumentProcessor()

            for doc_id in req.document_ids:
                try:
                    await processor.process_document(
                        doc_id,
                        session,
                        document_type_override=req.document_type,
                        force_reprocess=False,
                    )
                except Exception:
                    logger.exception(
                        "Batch extraction failed for document %s",
                        doc_id,
                    )

            await session.commit()

    background_tasks.add_task(_process_all)
    return {
        "message": f"Batch extraction started for {len(req.document_ids)} documents",
        "document_ids": req.document_ids,
    }


# ────────────────────────── Documents ───────────────────────────────────────

@documents_router.get("", response_model=list[dict])
async def list_documents(
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    batch_id: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).options(
        selectinload(Document.extraction_result),
        selectinload(Document.pages),
    )
    if document_type:
        stmt = stmt.where(Document.document_type == document_type)
    if status:
        stmt = stmt.where(Document.status == status)
    if batch_id:
        stmt = stmt.where(Document.batch_id == batch_id)
    if search:
        query = f"%{search}%"
        stmt = stmt.where(
            or_(
                Document.original_filename.ilike(query),
                Document.filename.ilike(query),
                Document.document_type.ilike(query),
            )
        )
    stmt = stmt.order_by(Document.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [_doc_to_dict(d) for d in docs]


@documents_router.get("/{doc_id}", response_model=dict)
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Document).options(
        selectinload(Document.extraction_result),
        selectinload(Document.pages),
    ).where(Document.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return _doc_to_dict(doc)


@documents_router.put("/{doc_id}/fields")
async def update_fields(
    doc_id: str,
    req: FieldUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ExtractionResult).where(ExtractionResult.document_id == doc_id)
    result = await db.execute(stmt)
    er = result.scalar_one_or_none()
    if not er:
        raise HTTPException(404, "Extraction result not found")

    er.corrected_fields = {**er.corrected_fields, **req.fields}
    er.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "Fields updated", "corrected_fields": er.corrected_fields}


@documents_router.patch("/{doc_id}/status")
async def update_status(
    doc_id: str,
    req: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    allowed_statuses = {"under_review", "approved", "extracted", "uploaded"}
    if req.status not in allowed_statuses:
        raise HTTPException(400, f"Invalid status. Allowed: {allowed_statuses}")

    stmt = select(Document).options(
        selectinload(Document.extraction_result),
        selectinload(Document.pages),
    ).where(Document.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    doc.status = req.status
    doc.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "Status updated", "status": doc.status}


@documents_router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Document).options(
        selectinload(Document.extraction_result),
        selectinload(Document.pages),
    ).where(Document.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    await db.delete(doc)
    await db.commit()
    return {"message": "Document deleted"}


@documents_router.get("/{doc_id}/preview")
async def get_preview(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Return base64 preview image with bounding boxes."""
    import base64
    from pathlib import Path

    stmt = select(Document).options(
        selectinload(Document.extraction_result),
        selectinload(Document.pages),
    ).where(Document.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    img_path = doc.preview_path or doc.preprocessed_path
    if not img_path and doc.pages:
        img_path = doc.pages[0].image_path
    if not img_path:
        file_path = Path(doc.file_path)
        if file_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}:
            img_path = doc.file_path

    if not img_path or not Path(img_path).exists():
        raise HTTPException(404, "Preview image not found")

    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".webp": "image/webp",
    }
    media_type = media_types.get(Path(img_path).suffix.lower(), "image/jpeg")

    return {
        "document_id": doc_id,
        "image_base64": b64,
        "media_type": media_type,
        "bounding_boxes": (doc.extraction_result.bounding_boxes if doc.extraction_result else []),
    }


@documents_router.get("/{doc_id}/tables")
async def get_tables(doc_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Document).options(
        selectinload(Document.extraction_result),
        selectinload(Document.pages),
    ).where(Document.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    tables = []
    if doc.extraction_result and doc.extraction_result.tables:
        tables = doc.extraction_result.tables

    return {"document_id": doc_id, "tables": tables}


# ────────────────────────── Batch ───────────────────────────────────────────

@batch_router.get("/{batch_id}/status", response_model=dict)
async def get_batch_status(batch_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Batch).where(Batch.id == batch_id)
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch not found")

    # Count docs
    count_stmt = select(func.count()).where(Document.batch_id == batch_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    done_stmt = select(func.count()).where(
        Document.batch_id == batch_id,
        Document.status.in_(["extracted", "approved", "under_review"]),
    )
    done = (await db.execute(done_stmt)).scalar() or 0

    failed_stmt = select(func.count()).where(
        Document.batch_id == batch_id, Document.status == "failed"
    )
    failed = (await db.execute(failed_stmt)).scalar() or 0

    progress = (done / total * 100) if total > 0 else 0

    # Get documents
    docs_stmt = select(Document).options(
        selectinload(Document.extraction_result),
        selectinload(Document.pages),
    ).where(Document.batch_id == batch_id)
    docs_result = await db.execute(docs_stmt)
    docs = docs_result.scalars().all()

    return {
        "id": batch.id,
        "name": batch.name,
        "status": batch.status,
        "total_documents": total,
        "processed_documents": done,
        "failed_documents": failed,
        "progress_percentage": round(progress, 1),
        "documents": [_doc_to_dict(d) for d in docs],
    }


# ────────────────────────── Export ──────────────────────────────────────────

@export_router.post("/export")
async def export_documents(
    req: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    requested_ids = list(dict.fromkeys(req.document_ids))
    if not requested_ids:
        raise HTTPException(400, "No document IDs provided")

    # Load documents
    stmt = select(Document).options(
        selectinload(Document.extraction_result),
        selectinload(Document.pages),
    ).where(Document.id.in_(requested_ids))
    result = await db.execute(stmt)
    docs = result.scalars().all()

    found_ids = {doc.id for doc in docs}
    missing_ids = [doc_id for doc_id in requested_ids if doc_id not in found_ids]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Some requested documents were not found",
                "missing_ids": missing_ids,
            },
        )

    docs_data = [_doc_to_dict(d) for d in docs]

    svc = ExportService()
    fmt = req.format.lower()

    if fmt == "json":
        content = svc.to_json(docs_data)
        media_type = "application/json"
        filename = "export.json"
    elif fmt == "csv":
        content = svc.to_csv(docs_data)
        media_type = "text/csv"
        filename = "export.csv"
    elif fmt == "xlsx":
        content = svc.to_xlsx(docs_data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "export.xlsx"
    elif fmt == "zip":
        content = svc.to_zip(docs_data, include_images=req.include_images)
        media_type = "application/zip"
        filename = "export.zip"
    else:
        raise HTTPException(400, f"Unknown format: {fmt}")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@export_router.post("/export/batch/{batch_id}")
async def export_batch(
    batch_id: str,
    format: str = "zip",
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).options(
        selectinload(Document.extraction_result),
        selectinload(Document.pages),
    ).where(Document.batch_id == batch_id)
    result = await db.execute(stmt)
    docs = result.scalars().all()
    if not docs:
        raise HTTPException(404, "Batch or documents not found")

    docs_data = [_doc_to_dict(d) for d in docs]
    req = ExportRequest(document_ids=[d["id"] for d in docs_data], format=format)
    return await export_documents(req, db)


# ────────────────────────── Templates ───────────────────────────────────────

@templates_router.get("/templates")
async def get_templates():
    """Return extraction schema templates per document type."""
    groq = GroqVisionService()
    templates = {}
    for doc_type in groq.DOCUMENT_TYPES:
        templates[doc_type] = groq._get_extraction_schema(doc_type)
    return {"templates": templates}


# ────────────────────────── Stats ───────────────────────────────────────────

@stats_router.get("/stats", response_model=dict)
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(Document.id)))).scalar() or 0

    # By status
    status_rows = await db.execute(
        select(Document.status, func.count()).group_by(Document.status)
    )
    by_status = {row[0]: row[1] for row in status_rows}

    # By type
    type_rows = await db.execute(
        select(Document.document_type, func.count()).group_by(Document.document_type)
    )
    by_type = {(row[0] or "unknown"): row[1] for row in type_rows}

    # Average confidence
    avg_conf = (
        await db.execute(select(func.avg(ExtractionResult.overall_confidence)))
    ).scalar()

    # Total batches
    total_batches = (await db.execute(select(func.count(Batch.id)))).scalar() or 0

    # Today's processing
    today = datetime.utcnow().date()
    today_stmt = select(func.count(Document.id)).where(
        func.date(Document.created_at) == today
    )
    today_count = (await db.execute(today_stmt)).scalar() or 0

    return {
        "total_documents": total,
        "by_status": by_status,
        "by_type": by_type,
        "average_confidence": round(float(avg_conf), 3) if avg_conf else None,
        "total_batches": total_batches,
        "processing_today": today_count,
    }


# ────────────────────────── Health ──────────────────────────────────────────

@health_router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    services = {}

    # DB check
    try:
        await db.execute(select(func.count(Document.id)))
        services["database"] = "ok"
    except Exception:
        services["database"] = "error"

    # Groq check
    from src.core.config import settings
    services["groq"] = "configured" if settings.groq_api_key else "not_configured"

    # OCR check
    try:
        
        import easyocr
        services["easyocr"] = "available"
    except ImportError:
        services["easyocr"] = "not_installed"

    return HealthResponse(
        status="ok" if all(v != "error" for v in services.values()) else "degraded",
        services=services,
    )
