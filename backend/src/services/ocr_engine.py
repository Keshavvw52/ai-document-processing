import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded EasyOCR reader cache
_easyocr_readers = {}


# ─────────────────────────────────────────────────────────────
# EasyOCR Loader
# ─────────────────────────────────────────────────────────────
def _get_easyocr(languages: list[str]):
    """
    Lazy-load EasyOCR model by language combination.
    Caches readers for reuse.
    """
    key = tuple(sorted(languages))

    if key not in _easyocr_readers:
        try:
            import easyocr

            _easyocr_readers[key] = easyocr.Reader(
                languages,
                gpu=False,
                verbose=False,
            )

            logger.info(f"EasyOCR initialized for languages: {languages}")

        except ImportError:
            logger.warning("EasyOCR not installed")
            return None

        except Exception as e:
            logger.error(f"EasyOCR initialization failed: {e}")
            return None

    return _easyocr_readers[key]


# ─────────────────────────────────────────────────────────────
# OCR Engine
# ─────────────────────────────────────────────────────────────
class OCREngine:
    """Dual OCR engine with EasyOCR + Tesseract fallback."""

    def __init__(self, languages: Optional[list[str]] = None):
        self.languages = languages or ["en"]

    # ─────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────
    def extract(self, image_path: str) -> dict:
        """
        Extract OCR data from image.

        Returns:
            {
                text,
                words,
                engine,
                language,
                average_confidence
            }
        """

        # Primary OCR
        result = self._run_easyocr(image_path)

        if result and result.get("text", "").strip():
            result["average_confidence"] = self.get_average_confidence(
                result["words"]
            )
            return result

        # Fallback OCR
        logger.info(
            f"EasyOCR empty/failed. Falling back to Tesseract: {image_path}"
        )

        result = self._run_tesseract(image_path)

        result["average_confidence"] = self.get_average_confidence(
            result["words"]
        )

        return result

    # ─────────────────────────────────────────────────────────
    # EasyOCR
    # ─────────────────────────────────────────────────────────
    def _run_easyocr(self, image_path: str) -> Optional[dict]:
        try:
            reader = _get_easyocr(self.languages)

            if reader is None:
                return None

            raw = reader.readtext(
                image_path,
                detail=1,
                paragraph=False,
            )

            words = []
            full_text_lines = []

            for bbox_points, text, confidence in raw:
                if not text.strip():
                    continue

                xs = [p[0] for p in bbox_points]
                ys = [p[1] for p in bbox_points]

                x1 = int(min(xs))
                y1 = int(min(ys))
                x2 = int(max(xs))
                y2 = int(max(ys))

                words.append(
                    {
                        "text": text.strip(),
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(float(confidence), 3),
                    }
                )

                full_text_lines.append(text.strip())

            return {
                "text": "\n".join(full_text_lines),
                "words": words,
                "engine": "easyocr",
                "language": self.languages[0],
            }

        except Exception as e:
            logger.error(f"EasyOCR failed for {image_path}: {e}")
            return None

    # ─────────────────────────────────────────────────────────
    # Tesseract
    # ─────────────────────────────────────────────────────────
    def _run_tesseract(self, image_path: str) -> dict:
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(image_path)

            lang_str = "+".join(self.languages)

            # Full OCR text
            text = pytesseract.image_to_string(
                img,
                lang=lang_str,
            )

            # Word-level boxes
            tsv_data = pytesseract.image_to_data(
                img,
                lang=lang_str,
                output_type=pytesseract.Output.DICT,
            )

            words = []

            n = len(tsv_data["text"])

            for i in range(n):
                word_text = tsv_data["text"][i].strip()

                try:
                    conf = float(tsv_data["conf"][i])
                except Exception:
                    conf = -1

                if not word_text or conf <= 0:
                    continue

                x = int(tsv_data["left"][i])
                y = int(tsv_data["top"][i])
                w = int(tsv_data["width"][i])
                h = int(tsv_data["height"][i])

                words.append(
                    {
                        "text": word_text,
                        "bbox": [x, y, x + w, y + h],
                        "confidence": round(conf / 100.0, 3),
                    }
                )

            return {
                "text": text.strip(),
                "words": words,
                "engine": "tesseract",
                "language": self.languages[0],
            }

        except ImportError:
            logger.error("pytesseract not installed")

        except Exception as e:
            logger.error(f"Tesseract failed for {image_path}: {e}")

        return {
            "text": "",
            "words": [],
            "engine": "none",
            "language": self.languages[0] if self.languages else "en",
        }

    # ─────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────
    def get_average_confidence(self, words: list[dict]) -> float:
        """
        Compute average OCR confidence score.
        """
        if not words:
            return 0.0

        confs = [
            word["confidence"]
            for word in words
            if word.get("confidence", 0) > 0
        ]

        if not confs:
            return 0.0

        return round(sum(confs) / len(confs), 3)

    def detect_low_confidence_fields(
        self,
        words: list[dict],
        threshold: float = 0.65,
    ) -> list[dict]:
        """
        Identify OCR fields requiring human review.
        """
        return [
            word
            for word in words
            if word.get("confidence", 0) < threshold
        ]

    def merge_ocr_results(
        self,
        primary: dict,
        fallback: dict,
    ) -> dict:
        """
        Optional future enhancement:
        Merge EasyOCR + Tesseract results.
        Currently returns primary unless empty.
        """
        if primary.get("text"):
            return primary
        return fallback

