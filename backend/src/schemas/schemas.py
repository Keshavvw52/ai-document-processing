"""
Pydantic v2 schemas for API validation and serialization.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


# ─────────────────────────── Document Schemas ──────────────────────────────

class DocumentBase(BaseModel):
    original_filename: str
    document_type: Optional[str] = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    page_count: int
    document_type: Optional[str]
    classification_confidence: Optional[float]
    status: str
    error_message: Optional[str]
    language_detected: Optional[str]
    batch_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]


class DocumentDetailResponse(DocumentResponse):
    extraction_result: Optional["ExtractionResultResponse"] = None
    pages: list["DocumentPageResponse"] = []


class DocumentPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    page_number: int
    ocr_text: Optional[str]
    extracted_data: Optional[dict]
    bounding_boxes: Optional[list]


# ─────────────────────────── Extraction Schemas ────────────────────────────

class ExtractionResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    fields: dict
    corrected_fields: dict
    confidence_scores: dict
    bounding_boxes: Optional[list]
    tables: Optional[list]
    overall_confidence: Optional[float]
    summary: Optional[str]
    ocr_engine: Optional[str]
    created_at: datetime
    updated_at: datetime


class FieldUpdateRequest(BaseModel):
    """Request to update/correct extracted fields."""
    fields: dict[str, Any] = Field(..., description="Field name → corrected value")


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., description="New status: under_review | approved | extracted")


# ─────────────────────────── Classification Schemas ────────────────────────

class ClassifyRequest(BaseModel):
    document_id: str


class ClassifyResponse(BaseModel):
    document_id: str
    document_type: str
    confidence: float
    all_scores: Optional[dict[str, float]] = None


# ─────────────────────────── Extract Schemas ───────────────────────────────

class ExtractRequest(BaseModel):
    document_id: str
    document_type: Optional[str] = None  # override auto-detection
    force_reprocess: bool = False


class BatchExtractRequest(BaseModel):
    document_ids: list[str]
    document_type: Optional[str] = None


# ─────────────────────────── Export Schemas ────────────────────────────────

class ExportRequest(BaseModel):
    document_ids: list[str]
    format: str = Field("json", description="json | csv | xlsx | zip")
    include_images: bool = False


# ─────────────────────────── Batch Schemas ────────────────────────────────

class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: Optional[str]
    status: str
    total_documents: int
    processed_documents: int
    successful_documents: int
    failed_documents: int
    review_needed: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class BatchStatusResponse(BatchResponse):
    progress_percentage: float
    documents: list[DocumentResponse] = []


# ─────────────────────────── Stats Schema ─────────────────────────────────

class StatsResponse(BaseModel):
    total_documents: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    average_confidence: Optional[float]
    total_batches: int
    processing_today: int


# ─────────────────────────── Upload Schema ────────────────────────────────

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str


class BatchUploadResponse(BaseModel):
    batch_id: str
    document_ids: list[str]
    total: int
    message: str


# ─────────────────────────── Health Schema ────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    services: dict[str, str]
