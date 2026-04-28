import base64
import json
import logging
from pathlib import Path
from typing import Optional

from groq import Groq
from src.core.config import settings

logger = logging.getLogger(__name__)


def _image_to_base64(image_path: str) -> tuple[str, str]:
    """Return (base64_data, media_type)."""
    suffix = Path(image_path).suffix.lower()
    type_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".bmp": "image/bmp",
        ".webp": "image/webp", ".tiff": "image/tiff",
    }
    media_type = type_map.get(suffix, "image/jpeg")
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, media_type


class GroqVisionService:
    """Wrapper around Groq's vision-capable LLM for document understanding."""

    DOCUMENT_TYPES = [
        "invoice", "receipt", "business_card", "form",
        "id_card", "contract", "report", "handwritten",
        "whiteboard", "table",
    ]

    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_vision_model
        self.max_tokens = settings.groq_max_tokens
        self.temperature = settings.groq_temperature

    # ──────────────────────────────────────────────────────────────────────
    # Classification
    # ──────────────────────────────────────────────────────────────────────

    def classify_document(self, image_path: str) -> dict:
        """
        Auto-classify a document image into one of the supported types.

        Returns: {"document_type": str, "confidence": float, "all_scores": dict}
        """
        b64, media_type = _image_to_base64(image_path)
        types_str = ", ".join(self.DOCUMENT_TYPES)

        prompt = f"""You are a document classification expert.

Examine the document image carefully and classify it into EXACTLY ONE of these categories:
{types_str}

Definitions:
- invoice: A bill from a vendor/supplier listing goods/services with amounts due
- receipt: Proof of payment/purchase (retail, restaurant, etc.)
- business_card: Contact information card for a person/company
- form: Structured form with labeled fields (application, registration, survey)
- id_card: Government/official identification (passport, driver's license, national ID)
- contract: Legal agreement/contract between parties
- report: Business report, letter, memo, or formal document
- handwritten: Primarily handwritten notes or filled handwritten form
- whiteboard: Photo of whiteboard with diagrams, text, or notes
- table: Document that is primarily tabular data / spreadsheet

Respond ONLY with valid JSON in this exact format:
{{
  "document_type": "<one of the categories above>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<brief 1-2 sentence explanation>",
  "all_scores": {{
    "invoice": <float>, "receipt": <float>, "business_card": <float>,
    "form": <float>, "id_card": <float>, "contract": <float>,
    "report": <float>, "handwritten": <float>, "whiteboard": <float>, "table": <float>
  }}
}}"""

        response = self._call_vision(prompt, b64, media_type)
        return self._parse_json_response(response, {
            "document_type": "form",
            "confidence": 0.5,
            "all_scores": {}
        })

    # ──────────────────────────────────────────────────────────────────────
    # Structured Extraction
    # ──────────────────────────────────────────────────────────────────────

    def extract_fields(
        self,
        image_path: str,
        document_type: str,
        ocr_text: Optional[str] = None
    ) -> dict:
        """
        Extract structured fields from a document.

        Returns: {"fields": {...}, "confidence_scores": {...}, "tables": [...], "summary": str}
        """
        b64, media_type = _image_to_base64(image_path)
        schema = self._get_extraction_schema(document_type)
        ocr_context = f"\n\nOCR text extracted (for reference):\n{ocr_text}" if ocr_text else ""

        prompt = f"""You are an expert document data extraction system.

Document type: {document_type.upper()}
{ocr_context}

Extract ALL visible fields from this document according to this schema:
{json.dumps(schema, indent=2)}

RULES:
1. Extract EXACTLY what is written - do not infer or hallucinate values
2. Use null for fields not present in the document
3. For line items / tables, extract every row
4. Provide confidence per field: "high" (clearly visible), "medium" (partially visible/inferred), "low" (guessed)
5. Preserve original formatting for numbers, dates, currencies

Respond ONLY with valid JSON in this exact format:
{{
  "fields": {{
    <extracted field-value pairs matching the schema>
  }},
  "confidence_scores": {{
    <field_name>: "high" | "medium" | "low"
  }},
  "tables": [
    {{
      "name": "<table description>",
      "headers": ["col1", "col2", ...],
      "rows": [["val1", "val2", ...], ...]
    }}
  ],
  "summary": "<2-3 sentence document summary>",
  "language": "<detected language code, e.g. en, fr, de>"
}}"""

        response = self._call_vision(prompt, b64, media_type)
        return self._parse_json_response(response, {
            "fields": {}, "confidence_scores": {}, "tables": [], "summary": ""
        })

    # ──────────────────────────────────────────────────────────────────────
    # Table Extraction
    # ──────────────────────────────────────────────────────────────────────

    def extract_tables(self, image_path: str, ocr_text: Optional[str] = None) -> list[dict]:
        """
        Detect and extract all tables from a document image.

        Returns list of table dicts: [{"headers": [...], "rows": [[...]]}]
        """
        b64, media_type = _image_to_base64(image_path)
        ocr_context = f"\nOCR text:\n{ocr_text}" if ocr_text else ""

        prompt = f"""You are a table extraction expert.{ocr_context}

Identify ALL tables in this document image.

For EACH table found:
1. Identify the header row (column names)
2. Extract every data row maintaining row/column alignment
3. Handle merged cells by repeating the value
4. Preserve numbers exactly as shown

Respond ONLY with valid JSON:
{{
  "tables": [
    {{
      "table_index": 0,
      "name": "<descriptive table name>",
      "headers": ["Column1", "Column2", ...],
      "rows": [
        ["row1col1", "row1col2", ...],
        ["row2col1", "row2col2", ...]
      ],
      "total_rows": <number>,
      "notes": "<any notes about merged cells, etc.>"
    }}
  ]
}}

If no tables exist, return {{"tables": []}}"""

        response = self._call_vision(prompt, b64, media_type)
        result = self._parse_json_response(response, {"tables": []})
        return result.get("tables", [])

    # ──────────────────────────────────────────────────────────────────────
    # Multi-page PDF summary
    # ──────────────────────────────────────────────────────────────────────

    def summarize_document(self, all_pages_text: str, document_type: str) -> str:
        """Generate an AI summary for a multi-page document."""
        prompt = f"""You are an expert document analyst.

Document type: {document_type}

Full extracted text from all pages:
{all_pages_text[:6000]}  

Write a concise 3-5 sentence summary covering:
- What this document is
- Key parties or entities involved
- Important dates, amounts, or terms
- Current status or key findings

Return ONLY the summary text, no JSON."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq summarize_document failed: {e}")
            return ""

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    def _call_vision(self, prompt: str, b64_image: str, media_type: str) -> str:
        """Make a vision call to Groq."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{b64_image}"
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq vision call failed: {e}")
            raise

    def _parse_json_response(self, response: str, fallback: dict) -> dict:
        """Parse JSON from LLM response, stripping markdown fences."""
        try:
            text = response.strip()
            # Strip ```json ... ``` fences
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"JSON parse failed: {e}\nResponse: {response[:500]}")
            return fallback

    def _get_extraction_schema(self, doc_type: str) -> dict:
        """Return the field schema for a given document type."""
        schemas = {
            "invoice": {
                "vendor_name": "string",
                "vendor_address": "string",
                "vendor_phone": "string",
                "vendor_email": "string",
                "invoice_number": "string",
                "invoice_date": "date (YYYY-MM-DD)",
                "due_date": "date (YYYY-MM-DD)",
                "po_number": "string",
                "currency": "string (e.g. USD)",
                "line_items": [{"description": "string", "quantity": "number", "unit_price": "number", "amount": "number"}],
                "subtotal": "number",
                "tax_rate": "number (percentage)",
                "tax_amount": "number",
                "discount": "number",
                "total": "number",
                "payment_terms": "string",
                "bank_details": {"bank_name": "string", "account_number": "string", "routing_number": "string"},
                "notes": "string",
            },
            "receipt": {
                "merchant_name": "string",
                "merchant_address": "string",
                "date": "date (YYYY-MM-DD)",
                "time": "string (HH:MM)",
                "receipt_number": "string",
                "items": [{"name": "string", "quantity": "number", "price": "number"}],
                "subtotal": "number",
                "tax": "number",
                "tip": "number",
                "total": "number",
                "currency": "string",
                "payment_method": "string (cash/credit/debit/etc.)",
                "card_last_four": "string",
            },
            "business_card": {
                "full_name": "string",
                "job_title": "string",
                "company": "string",
                "email": "string",
                "phone_primary": "string",
                "phone_secondary": "string",
                "address": "string",
                "website": "string",
                "linkedin": "string",
                "twitter": "string",
                "other_social": "string",
            },
            "form": {
                "form_title": "string",
                "form_number": "string",
                "fields": [{"label": "string", "value": "string", "field_type": "text|checkbox|radio|signature"}],
                "date": "string",
                "signatures_present": "boolean",
                "checkboxes": [{"label": "string", "checked": "boolean"}],
            },
            "id_card": {
                "document_type": "string (passport/national_id/driver_license)",
                "full_name": "string",
                "date_of_birth": "date (YYYY-MM-DD)",
                "id_number": "string",
                "nationality": "string",
                "gender": "string",
                "issue_date": "date (YYYY-MM-DD)",
                "expiry_date": "date (YYYY-MM-DD)",
                "address": "string",
                "issuing_authority": "string",
                "mrz_line1": "string",
                "mrz_line2": "string",
                "has_photo": "boolean",
            },
            "contract": {
                "contract_title": "string",
                "party_1_name": "string",
                "party_1_role": "string",
                "party_2_name": "string",
                "party_2_role": "string",
                "effective_date": "date (YYYY-MM-DD)",
                "end_date": "date (YYYY-MM-DD)",
                "contract_term": "string",
                "governing_law": "string",
                "payment_terms": "string",
                "payment_amount": "number",
                "currency": "string",
                "termination_notice_days": "number",
                "key_obligations_party1": ["string"],
                "key_obligations_party2": ["string"],
                "termination_clauses": "string",
                "confidentiality_clause": "boolean",
                "non_compete_clause": "boolean",
                "signatures": [{"name": "string", "date": "string", "present": "boolean"}],
            },
            "report": {
                "title": "string",
                "sender": "string",
                "recipient": "string",
                "date": "date (YYYY-MM-DD)",
                "reference_number": "string",
                "subject": "string",
                "executive_summary": "string",
                "key_findings": ["string"],
                "recommendations": ["string"],
                "action_items": [{"item": "string", "owner": "string", "deadline": "string"}],
                "conclusion": "string",
            },
            "handwritten": {
                "transcribed_text": "string (best effort full transcription)",
                "key_points": ["string"],
                "action_items": ["string"],
                "dates_mentioned": ["string"],
                "names_mentioned": ["string"],
                "numbers_mentioned": ["string"],
                "legibility": "high|medium|low",
            },
            "whiteboard": {
                "transcribed_text": "string",
                "diagrams_described": ["string"],
                "key_topics": ["string"],
                "action_items": ["string"],
                "attendees": ["string"],
                "date": "string",
            },
            "table": {
                "table_title": "string",
                "source": "string",
                "date": "string",
                "tables": [{"headers": ["string"], "rows": [["string"]]}],
                "summary": "string",
            },
        }
        return schemas.get(doc_type, {"raw_text": "string", "key_fields": [{"key": "string", "value": "string"}]})
