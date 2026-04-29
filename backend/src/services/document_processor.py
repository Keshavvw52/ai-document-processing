"""
Document Processing Orchestrator.

Coordinates the full pipeline:
  upload → preprocess → OCR → classify → LLM extraction → save results
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select

from src.core.config import settings
from src.models.models import Document, DocumentPage, ExtractionResult
from src.services.image_preprocessor import ImagePreprocessor
from src.services.ocr_engine import OCREngine
from src.services.groq_vision import GroqVisionService
from src.services.pdf_processor import PDFProcessor
from src.services.bbox_renderer import BBoxRenderer

logger = logging.getLogger(__name__)


def _confidence_to_score(value) -> float:
    """Convert varied LLM confidence shapes into a numeric score."""
    confidence_values = {"high": 0.9, "medium": 0.6, "low": 0.3}

    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized.endswith("%"):
            try:
                return max(0.0, min(1.0, float(normalized.rstrip("%")) / 100))
            except ValueError:
                return 0.5
        return confidence_values.get(normalized, 0.5)

    if isinstance(value, dict):
        for key in ("confidence", "score", "level", "value"):
            if key in value:
                return _confidence_to_score(value[key])
        return 0.5

    return 0.5


class DocumentProcessor:
    """Full pipeline orchestrator for single documents."""

    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.ocr = OCREngine(languages=settings.ocr_languages.split(","))
        self.groq = GroqVisionService()
        self.pdf = PDFProcessor()
        self.bbox_renderer = BBoxRenderer()

    async def process_document(
        self,
        document_id: str,
        db: AsyncSession,
        document_type_override: Optional[str] = None,
        force_reprocess: bool = False,
    ) -> dict:
        """
        Run full extraction pipeline for a document.
        Updates DB status at each step.
        """
        # Load document from DB
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            raise ValueError(f"Document {document_id} not found")

        if doc.status == "approved" and not force_reprocess:
            logger.info(f"Document {document_id} already approved, skipping")
            return {"status": "skipped", "reason": "already_approved"}

        try:
            # ── Step 1: Preprocessing ─────────────────────────────────────
            await self._update_status(doc, "preprocessing", db)

            file_path = doc.file_path
            mime = doc.mime_type
            is_pdf = mime == "application/pdf" or file_path.endswith(".pdf")

            if is_pdf:
                pages_data = await self._process_pdf_document(doc, db)
                primary_image = pages_data[0]["image_path"] if pages_data else file_path
            else:
                primary_image = file_path
                pages_data = []

            # Preprocessed artifacts are always images, even when the source is a PDF.
            artifact_stem = Path(doc.filename).stem
            preprocess_out = settings.upload_path / f"preprocessed_{artifact_stem}.png"
            preprocess_result = self.preprocessor.preprocess(
                primary_image, str(preprocess_out)
            )
            doc.preprocessed_path = preprocess_result["output_path"]
            await db.commit()

            # ── Step 2: OCR ───────────────────────────────────────────────
            await self._update_status(doc, "ocr_processing", db)

            ocr_result = self.ocr.extract(preprocess_result["output_path"])
            doc.ocr_text = ocr_result["text"]
            doc.language_detected = ocr_result.get("language", "en")
            await db.commit()

            # ── Step 3: Classification ────────────────────────────────────
            doc_type = document_type_override
            if not doc_type:
                classify_result = self.groq.classify_document(preprocess_result["output_path"])
                doc_type = classify_result.get("document_type", "form")
                doc.document_type = doc_type
                doc.classification_confidence = classify_result.get("confidence", 0.5)
                await db.commit()
            else:
                doc.document_type = doc_type
                await db.commit()

            # ── Step 4: LLM Extraction ────────────────────────────────────
            await self._update_status(doc, "extracting", db)

            extraction = self.groq.extract_fields(
                preprocess_result["output_path"],
                doc_type,
                ocr_text=ocr_result["text"]
            )

            # Extract tables
            tables = self.groq.extract_tables(
                preprocess_result["output_path"],
                ocr_text=ocr_result["text"]
            )

            # Summary for multi-page or contracts/reports
            summary = ""
            if doc_type in ("contract", "report") or (is_pdf and doc.page_count > 1):
                all_text = ocr_result["text"]
                if is_pdf and pages_data:
                    all_text = "\n\n".join(
                        p.get("ocr_text", "") for p in pages_data if p.get("ocr_text")
                    )
                summary = self.groq.summarize_document(all_text, doc_type)

            # ── Step 5: Bounding Box Render ───────────────────────────────
            word_bboxes = self.bbox_renderer.words_to_bbox_items(ocr_result.get("words", []))
            preview_out = settings.upload_path / f"preview_{artifact_stem}.jpg"
            preview_path = self.bbox_renderer.render(
                preprocess_result["output_path"],
                word_bboxes,
                str(preview_out),
            )
            doc.preview_path = preview_path

            # ── Step 6: Compute overall confidence ────────────────────────
            conf_scores = extraction.get("confidence_scores", {})
            if conf_scores:
                avg_conf = sum(
                    _confidence_to_score(v) for v in conf_scores.values()
                ) / len(conf_scores)
            else:
                avg_conf = self.ocr.get_average_confidence(ocr_result.get("words", []))

            # ── Step 7: Save extraction result ────────────────────────────
            # Check if result already exists
            stmt2 = select(ExtractionResult).where(
                ExtractionResult.document_id == document_id
            )
            res2 = await db.execute(stmt2)
            existing = res2.scalar_one_or_none()

            if existing:
                existing.fields = extraction.get("fields", {})
                existing.confidence_scores = conf_scores
                existing.tables = tables
                existing.overall_confidence = round(avg_conf, 3)
                existing.summary = summary
                existing.ocr_engine = ocr_result.get("engine", "easyocr")
                existing.bounding_boxes = word_bboxes
            else:
                new_result = ExtractionResult(
                    document_id=document_id,
                    fields=extraction.get("fields", {}),
                    corrected_fields={},
                    confidence_scores=conf_scores,
                    bounding_boxes=word_bboxes,
                    tables=tables,
                    overall_confidence=round(avg_conf, 3),
                    summary=summary,
                    ocr_engine=ocr_result.get("engine", "easyocr"),
                )
                db.add(new_result)

            # ── Step 8: Finalize ──────────────────────────────────────────
            doc.status = "extracted"
            doc.processed_at = datetime.utcnow()
            # Flag for review if low confidence
            if avg_conf < 0.6:
                doc.status = "under_review"

            await db.commit()
            logger.info(f"Document {document_id} processed successfully (type={doc_type})")

            return {
                "status": "success",
                "document_type": doc_type,
                "confidence": avg_conf,
                "fields_count": len(extraction.get("fields", {})),
                "tables_count": len(tables),
            }

        except Exception as e:
            logger.error(f"Processing failed for {document_id}: {e}", exc_info=True)
            doc.status = "failed"
            doc.error_message = str(e)
            await db.commit()
            raise

    async def _process_pdf_document(
        self, doc: Document, db: AsyncSession
    ) -> list[dict]:
        """Process each page of a PDF document."""
        pages_dir = settings.upload_path / f"pages_{doc.id}"
        pages_info = self.pdf.process_pdf(doc.file_path, str(pages_dir))

        doc.page_count = len(pages_info)
        await db.execute(delete(DocumentPage).where(DocumentPage.document_id == doc.id))
        await db.commit()

        pages_data = []
        for page_info in pages_info:
            # OCR each page
            page_ocr = self.ocr.extract(page_info["image_path"])

            # Save to DB
            db_page = DocumentPage(
                document_id=doc.id,
                page_number=page_info["page_number"],
                image_path=page_info["image_path"],
                thumbnail_path=page_info.get("thumbnail_path"),
                ocr_text=page_ocr["text"],
                bounding_boxes=self.bbox_renderer.words_to_bbox_items(
                    page_ocr.get("words", [])
                ),
            )
            db.add(db_page)
            pages_data.append({**page_info, "ocr_text": page_ocr["text"]})

        await db.commit()
        return pages_data

    async def _update_status(self, doc: Document, status: str, db: AsyncSession):
        doc.status = status
        await db.commit()
        logger.info(f"Document {doc.id}: status → {status}")
