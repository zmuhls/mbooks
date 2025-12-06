"""LLM-powered vision extraction for book metadata."""

import os
import json
import base64
import mimetypes
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


@dataclass
class ExtractionResult:
    """Result of vision extraction."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    raw_response: str = ""
    error: Optional[str] = None
    model_used: str = ""
    tokens_used: int = 0
    extraction_time: float = 0.0


class VisionExtractor:
    """Extract book metadata from images using LLM vision capabilities."""

    EXTRACTION_PROMPT = """Analyze this book image and extract all visible metadata.
Return a valid JSON object with these fields (use null for unknown values):

{
    "title": "Full book title",
    "subtitle": "Subtitle if visible",
    "author": "Author name(s)",
    "editor": "Editor name(s) for anthologies",
    "illustrator": "Illustrator if credited",
    "publisher": "Publisher name",
    "publication_year": 2024,
    "isbn": "ISBN if visible",
    "edition_info": "Edition statement (First Edition, Limited Edition, etc.)",
    "limitation_statement": "e.g., 'Limited to 500 copies'",
    "copy_number": "Copy number or letter if visible",
    "is_signed": true,
    "signed_by": "Name(s) of signatories",
    "binding_type": "Leather/Cloth/Paper/Board",
    "binding_color": "Color of binding",
    "format": "Hardcover/Paperback",
    "has_dust_jacket": false,
    "has_slipcase": false,
    "gilt_details": "Gold gilt spine lettering, etc.",
    "condition_observations": ["List of condition observations"],
    "special_features": ["List of special features"],
    "visible_text": "Any other significant text visible",
    "image_type": "cover/spine/title_page/signature_page/interior/slipcase"
}

Focus on accuracy. Only include information clearly visible in the image.
Return ONLY valid JSON, no markdown formatting or explanation."""

    CONDITION_PROMPT = """Assess the condition of this book from the image.

Return a valid JSON object:

{
    "overall_grade": "LIKE_NEW",
    "condition_summary": "Brief overall assessment",
    "cover_condition": "Description of cover condition",
    "spine_condition": "Description of spine condition",
    "page_condition": "Description if visible",
    "dust_jacket_condition": "If applicable",
    "slipcase_condition": "If applicable",
    "defects": ["List of any defects or wear"],
    "positive_features": ["List of positive condition attributes"]
}

Grades: NEW, LIKE_NEW, VERY_GOOD, GOOD, ACCEPTABLE
Return ONLY valid JSON."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-5-20250929"):
        """Initialize the vision extractor.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model: Model to use for extraction.
        """
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY or pass api_key.")

        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def _encode_image(self, image_path: Path) -> tuple[str, str]:
        """Encode image to base64 with media type detection."""
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if not mime_type:
            mime_type = "image/jpeg"

        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        return image_data, mime_type

    def extract_metadata(self, image_paths: List[Path]) -> ExtractionResult:
        """Extract metadata from one or more book images.

        Args:
            image_paths: List of paths to book images.

        Returns:
            ExtractionResult with extracted metadata.
        """
        start_time = datetime.now()

        # Build message content with images
        content = []
        for img_path in image_paths:
            if not img_path.exists():
                continue

            image_data, media_type = self._encode_image(img_path)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data
                }
            })

        if not content:
            return ExtractionResult(
                success=False,
                error="No valid images provided"
            )

        # Add extraction prompt
        content.append({
            "type": "text",
            "text": self.EXTRACTION_PROMPT
        })

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": content}]
            )

            raw_text = response.content[0].text
            elapsed = (datetime.now() - start_time).total_seconds()

            # Parse JSON from response
            try:
                # Handle potential markdown code blocks
                json_text = raw_text
                if "```json" in json_text:
                    json_text = json_text.split("```json")[1].split("```")[0]
                elif "```" in json_text:
                    json_text = json_text.split("```")[1].split("```")[0]

                data = json.loads(json_text.strip())

                return ExtractionResult(
                    success=True,
                    data=data,
                    raw_response=raw_text,
                    model_used=self.model,
                    tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                    extraction_time=elapsed
                )

            except json.JSONDecodeError as e:
                return ExtractionResult(
                    success=False,
                    raw_response=raw_text,
                    error=f"Failed to parse JSON: {e}",
                    model_used=self.model
                )

        except Exception as e:
            return ExtractionResult(
                success=False,
                error=str(e),
                model_used=self.model
            )

    def assess_condition(self, image_paths: List[Path]) -> ExtractionResult:
        """Assess book condition from images.

        Args:
            image_paths: List of paths to book images.

        Returns:
            ExtractionResult with condition assessment.
        """
        start_time = datetime.now()

        content = []
        for img_path in image_paths:
            if not img_path.exists():
                continue

            image_data, media_type = self._encode_image(img_path)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data
                }
            })

        if not content:
            return ExtractionResult(
                success=False,
                error="No valid images provided"
            )

        content.append({
            "type": "text",
            "text": self.CONDITION_PROMPT
        })

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": content}]
            )

            raw_text = response.content[0].text
            elapsed = (datetime.now() - start_time).total_seconds()

            try:
                json_text = raw_text
                if "```json" in json_text:
                    json_text = json_text.split("```json")[1].split("```")[0]
                elif "```" in json_text:
                    json_text = json_text.split("```")[1].split("```")[0]

                data = json.loads(json_text.strip())

                return ExtractionResult(
                    success=True,
                    data=data,
                    raw_response=raw_text,
                    model_used=self.model,
                    tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                    extraction_time=elapsed
                )

            except json.JSONDecodeError as e:
                return ExtractionResult(
                    success=False,
                    raw_response=raw_text,
                    error=f"Failed to parse JSON: {e}",
                    model_used=self.model
                )

        except Exception as e:
            return ExtractionResult(
                success=False,
                error=str(e),
                model_used=self.model
            )

    def extract_full(self, image_paths: List[Path]) -> Dict[str, Any]:
        """Perform full extraction: metadata + condition assessment.

        Args:
            image_paths: List of paths to book images.

        Returns:
            Combined extraction results.
        """
        metadata_result = self.extract_metadata(image_paths)
        condition_result = self.assess_condition(image_paths)

        combined = {
            "extraction_success": metadata_result.success,
            "condition_success": condition_result.success,
            "metadata": metadata_result.data if metadata_result.success else {},
            "condition": condition_result.data if condition_result.success else {},
            "total_tokens": metadata_result.tokens_used + condition_result.tokens_used,
            "errors": []
        }

        if not metadata_result.success:
            combined["errors"].append(f"Metadata: {metadata_result.error}")
        if not condition_result.success:
            combined["errors"].append(f"Condition: {condition_result.error}")

        return combined


def create_extractor(config: Optional[Dict] = None) -> VisionExtractor:
    """Factory function to create extractor from config."""
    if config is None:
        return VisionExtractor()

    return VisionExtractor(
        api_key=config.get('api_key'),
        model=config.get('model', 'claude-sonnet-4-5-20250929')
    )
