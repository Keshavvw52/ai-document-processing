import logging
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────
# Field Color Mapping
# ────────────────────────────────────────────────────
FIELD_COLORS = {
    # Financial
    "total": (46, 204, 113),
    "subtotal": (39, 174, 96),
    "tax": (52, 152, 219),
    "tax_amount": (52, 152, 219),
    "amount": (46, 204, 113),

    # Dates
    "date": (155, 89, 182),
    "invoice_date": (155, 89, 182),
    "due_date": (142, 68, 173),
    "expiry_date": (142, 68, 173),

    # Names / IDs
    "vendor_name": (231, 76, 60),
    "merchant_name": (231, 76, 60),
    "full_name": (231, 76, 60),
    "invoice_number": (230, 126, 34),
    "receipt_number": (230, 126, 34),
    "id_number": (230, 126, 34),

    # Contact
    "email": (26, 188, 156),
    "phone": (22, 160, 133),
    "address": (149, 165, 166),
    "website": (41, 128, 185),

    # OCR generic
    "ocr_word": (127, 140, 141),

    # Low confidence
    "low_confidence": (231, 76, 60),

    # Default
    "default": (52, 73, 94),
}


class BBoxRenderer:
    """Draws extraction bounding boxes onto document images."""

    def __init__(self):
        self.font = self._load_font()

    # ─────────────────────────────────────────────────────────
    # Main Render Method
    # ─────────────────────────────────────────────────────────
    def render(
        self,
        image_path: str,
        bounding_boxes: list[dict],
        output_path: Optional[str] = None,
        alpha: float = 0.35,
        show_labels: bool = True,
        highlight_low_confidence: bool = True,
    ) -> str:
        """
        Render annotated image.

        bounding_boxes:
        [
            {
                "field": str,
                "text": str,
                "bbox": [x1,y1,x2,y2],
                "confidence": float
            }
        ]
        """

        if output_path is None:
            p = Path(image_path)
            output_path = str(p.parent / f"annotated_{p.stem}.jpg")

        try:
            img = Image.open(image_path).convert("RGBA")

            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))

            draw_overlay = ImageDraw.Draw(overlay)
            draw_main = ImageDraw.Draw(img)

            for item in bounding_boxes:
                bbox = item.get("bbox", [])
                field = item.get("field", "default")
                text = item.get("text", "")
                confidence = float(item.get("confidence", 1.0))

                if len(bbox) != 4:
                    continue

                x1, y1, x2, y2 = map(int, bbox)

                # Confidence-based coloring
                if highlight_low_confidence and confidence < 0.65:
                    color = FIELD_COLORS["low_confidence"]
                else:
                    color = FIELD_COLORS.get(
                        field,
                        FIELD_COLORS["default"],
                    )

                opacity = int(alpha * 255)

                # ── Fill ───────────────────────────────────────
                draw_overlay.rectangle(
                    [x1, y1, x2, y2],
                    fill=(*color, opacity),
                )

                # ── Border ─────────────────────────────────────
                border_width = 3 if confidence < 0.65 else 2

                draw_main.rectangle(
                    [x1, y1, x2, y2],
                    outline=(*color, 255),
                    width=border_width,
                )

                # ── Labels ─────────────────────────────────────
                if show_labels:
                    label = self._build_label(
                        field,
                        text,
                        confidence,
                    )

                    self._draw_label(
                        draw_main,
                        x1,
                        y1,
                        label,
                        color,
                    )

            # Merge overlays
            final_img = Image.alpha_composite(
                img,
                overlay,
            ).convert("RGB")

            Path(output_path).parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            final_img.save(
                output_path,
                "JPEG",
                quality=92,
            )

            return output_path

        except Exception as e:
            logger.error(f"BBox rendering failed: {e}")
            return image_path

    # ─────────────────────────────────────────────────────────
    # OCR Word Conversion
    # ─────────────────────────────────────────────────────────
    def words_to_bbox_items(
        self,
        words: list[dict],
    ) -> list[dict]:
        """
        Convert OCR words into generic bbox items.
        """

        return [
            {
                "field": "ocr_word",
                "text": word["text"],
                "bbox": word["bbox"],
                "confidence": word.get(
                    "confidence",
                    1.0,
                ),
            }
            for word in words
        ]

    # ─────────────────────────────────────────────────────────
    # Label Builder
    # ─────────────────────────────────────────────────────────
    def _build_label(
        self,
        field: str,
        text: str,
        confidence: float,
    ) -> str:
        """
        Build field label.
        """
        text_preview = text[:20].replace("\n", " ")

        confidence_pct = int(confidence * 100)

        return f"{field} ({confidence_pct}%): {text_preview}"

    # ─────────────────────────────────────────────────────────
    # Draw Label
    # ─────────────────────────────────────────────────────────
    def _draw_label(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        label: str,
        color: tuple,
    ):
        """
        Draw text label box.
        """

        try:
            text_bbox = draw.textbbox(
                (x, y),
                label,
                font=self.font,
            )

            label_height = text_bbox[3] - text_bbox[1]
            label_width = text_bbox[2] - text_bbox[0]

            label_y = max(0, y - label_height - 4)

            draw.rectangle(
                [
                    x,
                    label_y,
                    x + label_width + 6,
                    label_y + label_height + 4,
                ],
                fill=(*color, 220),
            )

            draw.text(
                (x + 3, label_y + 2),
                label,
                fill=(255, 255, 255),
                font=self.font,
            )

        except Exception as e:
            logger.warning(f"Label draw failed: {e}")

    # ─────────────────────────────────────────────────────────
    # Font Loader
    # ─────────────────────────────────────────────────────────
    def _load_font(self):
        """
        Attempt to load a readable font.
        """
        try:
            return ImageFont.truetype("arial.ttf", 14)
        except Exception:
            return ImageFont.load_default()

    # ─────────────────────────────────────────────────────────
    # Confidence Filter
    # ─────────────────────────────────────────────────────────
    def filter_low_confidence(
        self,
        bounding_boxes: list[dict],
        threshold: float = 0.65,
    ) -> list[dict]:
        """
        Return only low-confidence fields for review.
        """

        return [
            box
            for box in bounding_boxes
            if box.get("confidence", 1.0) < threshold
        ]

