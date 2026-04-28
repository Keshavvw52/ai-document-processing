import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF


logger = logging.getLogger(__name__)


class PDFProcessor:
    """Processes PDFs into OCR-compatible page images."""

    DEFAULT_DPI = 200
    THUMBNAIL_DPI = 72
    MAX_PAGES_WARNING = 100

    # ─────────────────────────────────────────────────────────────
    # Main PDF Processing
    # ─────────────────────────────────────────────────────────────
    def process_pdf(
        self,
        pdf_path: str,
        output_dir: str,
        dpi: int = DEFAULT_DPI,
        generate_thumbnails: bool = True,
        max_pages: Optional[int] = None,
    ) -> list[dict]:
        """
        Convert PDF pages into images.

        Returns:
            [
                {
                    "page_number": int,
                    "image_path": str,
                    "thumbnail_path": Optional[str],
                    "width": int,
                    "height": int,
                    "embedded_text": Optional[str],
                    "has_embedded_text": bool,
                }
            ]
        """

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        pages = []

        try:
            doc = fitz.open(pdf_path)

            total_pages = len(doc)

            if total_pages > self.MAX_PAGES_WARNING:
                logger.warning(
                    f"Large PDF detected ({total_pages} pages): {pdf_path}"
                )

            if max_pages:
                total_pages = min(total_pages, max_pages)

            logger.info(
                f"Processing PDF: {pdf_path} ({total_pages} pages)"
            )

            for page_num in range(total_pages):
                page = doc[page_num]
                page_number = page_num + 1

                # ── Full-resolution render ───────────────────────
                full_matrix = fitz.Matrix(dpi / 72, dpi / 72)

                pix = page.get_pixmap(
                    matrix=full_matrix,
                    alpha=False,
                )

                img_path = str(
                    out_dir / f"page_{page_number:03d}.png"
                )

                pix.save(img_path)

                # ── Thumbnail render ─────────────────────────────
                thumb_path = None

                if generate_thumbnails:
                    thumb_matrix = fitz.Matrix(
                        self.THUMBNAIL_DPI / 72,
                        self.THUMBNAIL_DPI / 72,
                    )

                    thumb_pix = page.get_pixmap(
                        matrix=thumb_matrix,
                        alpha=False,
                    )

                    thumb_path = str(
                        out_dir / f"thumb_{page_number:03d}.png"
                    )

                    thumb_pix.save(thumb_path)

                # ── Embedded text extraction ─────────────────────
                embedded_text = page.get_text("text").strip()

                pages.append(
                    {
                        "page_number": page_number,
                        "image_path": img_path,
                        "thumbnail_path": thumb_path,
                        "width": pix.width,
                        "height": pix.height,
                        "embedded_text": embedded_text,
                        "has_embedded_text": bool(embedded_text),
                    }
                )

            doc.close()

        except Exception as e:
            logger.error(f"PDF processing failed for {pdf_path}: {e}")
            raise RuntimeError(f"Failed to process PDF: {e}")

        return pages

    # ─────────────────────────────────────────────────────────────
    # Page Count
    # ─────────────────────────────────────────────────────────────
    def get_page_count(self, pdf_path: str) -> int:
        """Return number of pages in PDF."""

        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count

        except Exception as e:
            logger.error(f"Could not read PDF page count: {e}")
            return 1

    # ─────────────────────────────────────────────────────────────
    # Embedded Text Extraction
    # ─────────────────────────────────────────────────────────────
    def extract_embedded_text(self, pdf_path: str) -> list[dict]:
        """
        Extract embedded digital text from PDF.

        Useful for:
        - Digital PDFs
        - Faster extraction
        - Cross-page summaries
        """

        results = []

        try:
            doc = fitz.open(pdf_path)

            for i, page in enumerate(doc):
                text = page.get_text("text").strip()

                results.append(
                    {
                        "page_number": i + 1,
                        "text": text,
                        "has_embedded_text": bool(text),
                    }
                )

            doc.close()

        except Exception as e:
            logger.error(
                f"Embedded text extraction failed for {pdf_path}: {e}"
            )

        return results

    # ─────────────────────────────────────────────────────────────
    # Full Document Text
    # ─────────────────────────────────────────────────────────────
    def extract_full_text(self, pdf_path: str) -> str:
        """
        Merge all embedded PDF text into one string.
        Useful for:
        - Contract summaries
        - Multi-page reports
        - Groq summarization
        """

        pages = self.extract_embedded_text(pdf_path)

        return "\n\n".join(
            page["text"]
            for page in pages
            if page["text"]
        )

    # ─────────────────────────────────────────────────────────────
    # PDF Metadata
    # ─────────────────────────────────────────────────────────────
    def get_pdf_metadata(self, pdf_path: str) -> dict:
        """
        Extract PDF metadata.
        """

        try:
            doc = fitz.open(pdf_path)

            metadata = doc.metadata or {}

            result = {
                "title": metadata.get("title"),
                "author": metadata.get("author"),
                "subject": metadata.get("subject"),
                "creator": metadata.get("creator"),
                "producer": metadata.get("producer"),
                "creation_date": metadata.get("creationDate"),
                "modification_date": metadata.get("modDate"),
                "page_count": len(doc),
            }

            doc.close()

            return result

        except Exception as e:
            logger.error(
                f"Metadata extraction failed for {pdf_path}: {e}"
            )

            return {
                "page_count": 1,
            }

    # ─────────────────────────────────────────────────────────────
    # OCR Necessity Detection
    # ─────────────────────────────────────────────────────────────
    def requires_ocr(self, pdf_path: str) -> bool:
        """
        Determine if PDF requires OCR.

        Returns:
            True -> scanned/image PDF
            False -> digital PDF with usable embedded text
        """

        pages = self.extract_embedded_text(pdf_path)

        if not pages:
            return True

        total_chars = sum(
            len(page["text"])
            for page in pages
        )

        return total_chars < 100  # Heuristic threshold

