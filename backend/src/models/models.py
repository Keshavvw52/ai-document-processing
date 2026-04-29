import uuid
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SAEnum,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class DocumentStatus(str, Enum):
    uploaded = "uploaded"
    preprocessing = "preprocessing"
    ocr_processing = "ocr_processing"
    extracting = "extracting"
    extracted = "extracted"
    under_review = "under_review"
    approved = "approved"
    failed = "failed"


class BatchStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    partial = "partial"
    failed = "failed"


class Document(Base):
    """Represents an uploaded document."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=gen_uuid
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)

    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    page_count: Mapped[int] = mapped_column(Integer, default=1)

    # Classification
    document_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    classification_confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Status
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus),
        default=DocumentStatus.uploaded,
        index=True,
    )

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Processing metadata
    preprocessed_path: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    preview_path: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )

    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language_detected: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )

    processing_time_seconds: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Batch reference
    batch_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("batches.id"),
        nullable=True,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Relationships
    extraction_result: Mapped[Optional["ExtractionResult"]] = relationship(
        "ExtractionResult",
        back_populates="document",
        cascade="all, delete-orphan",
        uselist=False,
    )

    pages: Mapped[list["DocumentPage"]] = relationship(
        "DocumentPage",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    batch: Mapped[Optional["Batch"]] = relationship(
        "Batch",
        back_populates="documents",
    )


# ─────────────────────────────────────────────────────────────
# Document Pages (Multi-page PDFs)
# ─────────────────────────────────────────────────────────────
class DocumentPage(Base):
    """Represents a single page in a multi-page document."""

    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=gen_uuid
    )

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id"),
        nullable=False,
        index=True,
    )

    page_number: Mapped[int] = mapped_column(Integer, nullable=False)

    image_path: Mapped[str] = mapped_column(String(512), nullable=False)

    thumbnail_path: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )

    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    extracted_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    bounding_boxes: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationship
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="pages",
    )


class ExtractionResult(Base):
    """Structured extraction output for a processed document."""

    __tablename__ = "extraction_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=gen_uuid
    )

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Structured extraction
    fields: Mapped[dict] = mapped_column(JSON, default=dict)

    corrected_fields: Mapped[dict] = mapped_column(JSON, default=dict)

    confidence_scores: Mapped[dict] = mapped_column(JSON, default=dict)

    bounding_boxes: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
    )

    tables: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
    )

    overall_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    ocr_engine: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationship
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="extraction_result",
    )


class Batch(Base):
    """Represents a batch processing job."""

    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=gen_uuid
    )

    name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[BatchStatus] = mapped_column(
        SAEnum(BatchStatus),
        default=BatchStatus.pending,
        index=True,
    )

    total_documents: Mapped[int] = mapped_column(Integer, default=0)

    processed_documents: Mapped[int] = mapped_column(Integer, default=0)

    successful_documents: Mapped[int] = mapped_column(Integer, default=0)

    failed_documents: Mapped[int] = mapped_column(Integer, default=0)

    review_needed: Mapped[int] = mapped_column(Integer, default=0)

    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Relationship
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="batch",
        cascade="all, delete",
    )

