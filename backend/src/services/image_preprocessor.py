import logging
import base64
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image


logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Comprehensive preprocessing pipeline for document OCR."""

    MIN_DPI = 150

    def preprocess(
        self,
        image_path: str,
        output_path: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> dict:
        """
        Full preprocessing pipeline.

        Returns:
            {
                output_path,
                operations_applied,
                dpi_warning,
                original_shape,
                output_shape
            }
        """

        opts = {
            "deskew": True,
            "denoise": True,
            "binarize": False,
            "clahe": True,
            "border_removal": True,
            "upscale_if_small": False,
            "grayscale": False,
            "manual_rotation": 0,
            "fast_mode": False,
            "save_debug_steps": False,
        }

        if options:
            opts.update(options)

        img = self._load_image(image_path)
        original_shape = img.shape
        operations = []
        dpi_warning = False

        debug_dir = None
        if opts["save_debug_steps"]:
            debug_dir = Path(image_path).parent / "debug_preprocessing"
            debug_dir.mkdir(parents=True, exist_ok=True)

        # ── DPI / Resolution Check ───────────────────────────────
        if self._is_low_resolution(image_path, img):
            dpi_warning = True
            logger.warning(f"Low resolution image detected: {img.shape}")

            if opts["upscale_if_small"]:
                img = self._upscale(img)
                operations.append("upscale_2x")
                self._save_debug(debug_dir, "upscaled.jpg", img)

        # ── Border Removal ───────────────────────────────────────
        if opts["border_removal"]:
            img = self._remove_borders(img)
            operations.append("border_removal")
            self._save_debug(debug_dir, "border_removed.jpg", img)

        # ── Manual Rotation ──────────────────────────────────────
        if opts["manual_rotation"]:
            img = self._rotate(img, opts["manual_rotation"])
            operations.append(f"manual_rotation({opts['manual_rotation']}°)")
            self._save_debug(debug_dir, "manual_rotated.jpg", img)

        # ── Deskew ───────────────────────────────────────────────
        if opts["deskew"]:
            img, angle = self._deskew(img)
            if abs(angle) > 0.5:
                operations.append(f"deskew({angle:.1f}°)")
                self._save_debug(debug_dir, "deskewed.jpg", img)

        # ── Denoise ──────────────────────────────────────────────
        if opts["denoise"]:
            img = self._denoise(img, fast_mode=opts["fast_mode"])
            operations.append("denoise")
            self._save_debug(debug_dir, "denoised.jpg", img)

        # ── CLAHE ────────────────────────────────────────────────
        if opts["clahe"]:
            img = self._apply_clahe(img)
            operations.append("clahe")
            self._save_debug(debug_dir, "clahe.jpg", img)

        # ── Grayscale ────────────────────────────────────────────
        if opts["grayscale"]:
            img = self._to_grayscale(img)
            operations.append("grayscale")
            self._save_debug(debug_dir, "grayscale.jpg", img)

        # ── Binarization ─────────────────────────────────────────
        if opts["binarize"]:
            img = self._binarize(img)
            operations.append("binarize")
            self._save_debug(debug_dir, "binarized.jpg", img)

        # ── Save Final Output ────────────────────────────────────
        if output_path is None:
            p = Path(image_path)
            output_path = str(p.parent / f"preprocessed_{p.name}")

        self._save_image(img, output_path)

        return {
            "output_path": output_path,
            "operations_applied": operations,
            "dpi_warning": dpi_warning,
            "original_shape": original_shape,
            "output_shape": img.shape,
        }

    # ─────────────────────────────────────────────────────────────
    # Core Helpers
    # ─────────────────────────────────────────────────────────────

    def _load_image(self, path: str) -> np.ndarray:
        """Load image safely using OpenCV or Pillow fallback."""
        try:
            img = cv2.imread(path)
            if img is None:
                pil_img = Image.open(path).convert("RGB")
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

            if img is None:
                raise ValueError("Image loading failed.")

            return img

        except Exception as e:
            logger.error(f"Failed to load image {path}: {e}")
            raise ValueError(f"Could not load image: {path}")

    def _save_image(self, img: np.ndarray, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(path, img)

    def _save_debug(self, debug_dir: Optional[Path], filename: str, img: np.ndarray):
        if debug_dir:
            cv2.imwrite(str(debug_dir / filename), img)

    def _is_low_resolution(self, image_path: str, img: np.ndarray) -> bool:
        """Check true DPI if available, else fallback to resolution heuristic."""
        try:
            pil_img = Image.open(image_path)
            dpi = pil_img.info.get("dpi", (72, 72))[0]
            return dpi < self.MIN_DPI
        except Exception:
            h, w = img.shape[:2]
            return w < 800 or h < 600

    def _upscale(self, img: np.ndarray, scale: float = 2.0) -> np.ndarray:
        h, w = img.shape[:2]
        return cv2.resize(
            img,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC,
        )

    def _remove_borders(self, img: np.ndarray) -> np.ndarray:
        gray = (
            cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if len(img.shape) == 3
            else img.copy()
        )

        _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        if not contours:
            return img

        largest = max(contours, key=cv2.contourArea)

        if cv2.contourArea(largest) < img.shape[0] * img.shape[1] * 0.2:
            return img

        x, y, w, h = cv2.boundingRect(largest)

        pad = 10
        x = max(0, x - pad)
        y = max(0, y - pad)
        w = min(img.shape[1] - x, w + pad * 2)
        h = min(img.shape[0] - y, h + pad * 2)

        return img[y : y + h, x : x + w]

    def _rotate(self, img: np.ndarray, angle: float) -> np.ndarray:
        h, w = img.shape[:2]
        center = (w // 2, h // 2)

        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        return cv2.warpAffine(
            img,
            M,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def _deskew(self, img: np.ndarray) -> tuple[np.ndarray, float]:
        gray = (
            cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if len(img.shape) == 3
            else img.copy()
        )

        gray = cv2.bitwise_not(gray)

        thresh = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY | cv2.THRESH_OTSU,
        )[1]

        coords = np.column_stack(np.where(thresh > 0))

        if len(coords) < 50:
            return img, 0.0

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90

        if abs(angle) < 0.3:
            return img, 0.0

        rotated = self._rotate(img, angle)

        return rotated, angle

    def _denoise(
        self,
        img: np.ndarray,
        fast_mode: bool = False,
    ) -> np.ndarray:
        if fast_mode:
            return cv2.GaussianBlur(img, (3, 3), 0)

        if len(img.shape) == 3:
            return cv2.fastNlMeansDenoisingColored(
                img,
                None,
                10,
                10,
                7,
                21,
            )

        return cv2.fastNlMeansDenoising(
            img,
            None,
            10,
            7,
            21,
        )

    def _apply_clahe(self, img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)

            l, a, b = cv2.split(lab)

            clahe = cv2.createCLAHE(
                clipLimit=2.0,
                tileGridSize=(8, 8),
            )

            l_clahe = clahe.apply(l)

            merged = cv2.merge([l_clahe, a, b])

            return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8),
        )

        return clahe.apply(img)

    def _to_grayscale(self, img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img

    def _binarize(self, img: np.ndarray) -> np.ndarray:
        gray = (
            cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if len(img.shape) == 3
            else img
        )

        return cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )

    # ─────────────────────────────────────────────────────────────
    # Additional Interfaces
    # ─────────────────────────────────────────────────────────────

    def preprocess_array(
        self,
        img: np.ndarray,
        options: Optional[dict] = None,
    ) -> np.ndarray:
        """Preprocess directly from numpy array."""
        temp_path = "temp_preprocess_input.jpg"
        cv2.imwrite(temp_path, img)

        result = self.preprocess(temp_path, options=options)

        return self._load_image(result["output_path"])

    def get_preprocessing_preview(self, image_path: str) -> dict:
        """
        Return before/after images as base64 strings for frontend preview.
        """

        result = self.preprocess(image_path)

        def img_to_b64(path: str) -> str:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()

        return {
            "original": img_to_b64(image_path),
            "preprocessed": img_to_b64(result["output_path"]),
            "operations": result["operations_applied"],
            "dpi_warning": result["dpi_warning"],
        }
