"""Schema validation for book metadata."""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Represents a validation error."""
    field: str
    message: str
    value: Any = None


class BookMetadataSchema:
    """Validates book metadata against schema rules."""

    CONDITION_GRADES = ["NEW", "LIKE_NEW", "VERY_GOOD", "GOOD", "ACCEPTABLE"]
    COPY_TYPES = ["numbered", "lettered", "none"]
    FORMATS = ["Hardcover", "Paperback", "Trade Paperback", "Mass Market Paperback", "Leather Bound"]
    BINDING_TYPES = ["Cloth", "Leather", "Half-Leather", "Full Leather", "Paper", "Board"]

    ISBN_10_PATTERN = re.compile(r'^[0-9]{9}[0-9X]$')
    ISBN_13_PATTERN = re.compile(r'^97[89][0-9]{10}$')

    def __init__(self):
        self.errors: List[ValidationError] = []

    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate metadata dictionary. Returns True if valid."""
        self.errors = []

        # Required fields
        self._require_field(data, 'basic_info.title', 'Title is required')

        # Validate ISBNs if present
        self._validate_isbn(data)

        # Validate condition grade
        self._validate_condition(data)

        # Validate year ranges
        self._validate_years(data)

        # Validate images
        self._validate_images(data)

        return len(self.errors) == 0

    def _require_field(self, data: Dict, path: str, message: str):
        """Check if a required field exists and is not empty."""
        value = self._get_nested(data, path)
        if not value:
            self.errors.append(ValidationError(path, message))

    def _get_nested(self, data: Dict, path: str) -> Any:
        """Get nested value using dot notation."""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def _validate_isbn(self, data: Dict):
        """Validate ISBN formats."""
        isbn_10 = self._get_nested(data, 'publication_details.isbn_10')
        isbn_13 = self._get_nested(data, 'publication_details.isbn_13')

        if isbn_10 and not self.ISBN_10_PATTERN.match(isbn_10):
            self.errors.append(ValidationError(
                'publication_details.isbn_10',
                'Invalid ISBN-10 format',
                isbn_10
            ))

        if isbn_13 and not self.ISBN_13_PATTERN.match(isbn_13):
            self.errors.append(ValidationError(
                'publication_details.isbn_13',
                'Invalid ISBN-13 format',
                isbn_13
            ))

    def _validate_condition(self, data: Dict):
        """Validate condition grade."""
        grade = self._get_nested(data, 'condition.overall_grade')
        if grade and grade not in self.CONDITION_GRADES:
            self.errors.append(ValidationError(
                'condition.overall_grade',
                f'Invalid condition grade. Must be one of: {", ".join(self.CONDITION_GRADES)}',
                grade
            ))

    def _validate_years(self, data: Dict):
        """Validate publication years are reasonable."""
        pub_year = self._get_nested(data, 'publication_details.publication_year')
        orig_year = self._get_nested(data, 'publication_details.original_publication_year')

        if pub_year:
            if not isinstance(pub_year, int) or pub_year < 1000 or pub_year > 2100:
                self.errors.append(ValidationError(
                    'publication_details.publication_year',
                    'Publication year must be between 1000 and 2100',
                    pub_year
                ))

        if orig_year:
            if not isinstance(orig_year, int) or orig_year < 1000 or orig_year > 2100:
                self.errors.append(ValidationError(
                    'publication_details.original_publication_year',
                    'Original publication year must be between 1000 and 2100',
                    orig_year
                ))

    def _validate_images(self, data: Dict):
        """Validate images structure."""
        files = self._get_nested(data, 'images.files')
        primary = self._get_nested(data, 'images.primary_image')

        if files and not isinstance(files, list):
            self.errors.append(ValidationError(
                'images.files',
                'Image files must be a list'
            ))

        if primary and files and primary not in files:
            self.errors.append(ValidationError(
                'images.primary_image',
                'Primary image must be in the files list',
                primary
            ))

    def get_errors_summary(self) -> str:
        """Get human-readable error summary."""
        if not self.errors:
            return "No validation errors"

        lines = ["Validation errors:"]
        for err in self.errors:
            lines.append(f"  - {err.field}: {err.message}")
            if err.value:
                lines.append(f"    (value: {err.value})")

        return "\n".join(lines)


def validate_listing(data: Dict[str, Any]) -> tuple[bool, List[ValidationError]]:
    """Convenience function to validate listing data."""
    schema = BookMetadataSchema()
    is_valid = schema.validate(data)
    return is_valid, schema.errors
