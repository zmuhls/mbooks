"""Match search results to metadata fields with confidence scoring.

Handles field validation, confidence calculation, and auto-accept logic.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .result_parser import ParsedField, PricingData

log = logging.getLogger(__name__)


@dataclass
class FieldMatch:
    """Represents a matched field value with metadata."""
    field_name: str
    value: Any
    confidence: float  # 0.0 - 1.0
    source_url: str
    source_type: str
    reasoning: str
    auto_accepted: bool = False
    user_accepted: Optional[bool] = None
    user_modified_value: Optional[Any] = None


@dataclass
class MatchResult:
    """Complete match results for a book."""
    matches: Dict[str, FieldMatch] = field(default_factory=dict)
    pricing: Optional[PricingData] = None
    missing_fields: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class FieldMatcher:
    """Match search results to metadata fields with confidence scoring."""

    # Source authority weights (higher = more trusted)
    SOURCE_AUTHORITY = {
        'ebay': 0.90,       # High for market data
        'abebooks': 0.95,   # Very high for bibliographic
        'amazon': 0.85,     # Good for ISBN/pages
        'worldcat': 0.95,   # Very high for bibliographic
        'goodreads': 0.80,  # Good for general info
        'json': 0.90,       # Structured data
        'text': 0.75,       # Extracted from text
        'web': 0.70,        # General web
    }

    # Field-specific source preferences
    FIELD_SOURCE_PREFERENCES = {
        'publisher': ['abebooks', 'worldcat', 'ebay', 'amazon'],
        'place_of_publication': ['ebay', 'abebooks', 'worldcat'],
        'isbn_10': ['amazon', 'abebooks', 'worldcat'],
        'isbn_13': ['amazon', 'abebooks', 'worldcat'],
        'page_count': ['amazon', 'abebooks', 'worldcat'],
        'genre': ['amazon', 'goodreads', 'ebay'],
        'binding': ['ebay', 'abebooks'],
        'publication_year': ['abebooks', 'worldcat', 'amazon'],
        'comparable_prices': ['ebay'],
    }

    # Auto-accept threshold
    AUTO_ACCEPT_THRESHOLD = 0.95

    # Minimum confidence to show
    MIN_DISPLAY_THRESHOLD = 0.50

    def __init__(
        self,
        auto_accept_threshold: float = 0.95,
        min_display_threshold: float = 0.50
    ):
        """Initialize field matcher.

        Args:
            auto_accept_threshold: Confidence above which to auto-accept
            min_display_threshold: Minimum confidence to show match
        """
        self.auto_accept_threshold = auto_accept_threshold
        self.min_display_threshold = min_display_threshold

    def match_fields(
        self,
        parsed_fields: List[ParsedField],
        existing_metadata: Dict[str, Any],
        pricing_data: Optional[PricingData] = None
    ) -> MatchResult:
        """Match parsed fields against existing metadata.

        Args:
            parsed_fields: Fields parsed from search results
            existing_metadata: Current metadata dict
            pricing_data: Pricing data if available

        Returns:
            MatchResult with all matches
        """
        result = MatchResult()
        result.pricing = pricing_data

        # Identify missing fields
        result.missing_fields = self._identify_missing(existing_metadata)

        # Process each parsed field
        for parsed in parsed_fields:
            # Skip if field already has value and this is lower confidence
            existing_value = self._get_existing_value(
                existing_metadata,
                parsed.field_name
            )

            if existing_value is not None:
                # Only override if significantly higher confidence
                if parsed.confidence < 0.95:
                    continue

            # Calculate adjusted confidence
            confidence = self._calculate_confidence(
                parsed,
                existing_metadata
            )

            if confidence < self.min_display_threshold:
                continue

            # Validate value
            is_valid, validation_msg = self._validate_value(
                parsed.field_name,
                parsed.value,
                existing_metadata
            )

            if not is_valid:
                result.errors.append(f"{parsed.field_name}: {validation_msg}")
                continue

            # Create match
            auto_accept = confidence >= self.auto_accept_threshold
            reasoning = self._generate_reasoning(parsed, confidence, auto_accept)

            match = FieldMatch(
                field_name=parsed.field_name,
                value=parsed.value,
                confidence=confidence,
                source_url=parsed.source,
                source_type=parsed.source_type,
                reasoning=reasoning,
                auto_accepted=auto_accept
            )

            # Keep highest confidence match per field
            existing_match = result.matches.get(parsed.field_name)
            if existing_match is None or confidence > existing_match.confidence:
                result.matches[parsed.field_name] = match

        return result

    def _calculate_confidence(
        self,
        parsed: ParsedField,
        existing: Dict[str, Any]
    ) -> float:
        """Calculate adjusted confidence for a parsed field.

        Factors:
        - Base confidence from parser
        - Source authority weight
        - Source preference for field type
        - Consistency with existing data

        Args:
            parsed: Parsed field
            existing: Existing metadata

        Returns:
            Adjusted confidence 0.0-1.0
        """
        base = parsed.confidence

        # Apply source authority
        source_weight = self.SOURCE_AUTHORITY.get(parsed.source_type, 0.70)
        confidence = base * source_weight

        # Boost if source is preferred for this field
        preferences = self.FIELD_SOURCE_PREFERENCES.get(parsed.field_name, [])
        if parsed.source_type in preferences:
            position = preferences.index(parsed.source_type)
            boost = 1.0 + (0.05 * (len(preferences) - position))
            confidence *= boost

        # Consistency check
        consistency_score = self._check_consistency(parsed, existing)
        confidence *= consistency_score

        # Cap at 1.0
        return min(confidence, 1.0)

    def _check_consistency(
        self,
        parsed: ParsedField,
        existing: Dict[str, Any]
    ) -> float:
        """Check if parsed value is consistent with existing data.

        Args:
            parsed: Parsed field
            existing: Existing metadata

        Returns:
            Consistency multiplier (0.5-1.1)
        """
        # If we have a year and this is a year, check consistency
        if parsed.field_name == 'publication_year':
            existing_year = self._get_existing_value(existing, 'publication_year')
            if existing_year:
                try:
                    diff = abs(int(parsed.value) - int(existing_year))
                    if diff == 0:
                        return 1.1  # Boost for exact match
                    elif diff <= 2:
                        return 1.0  # Reasonable variance
                    else:
                        return 0.7  # Suspicious difference
                except (ValueError, TypeError):
                    pass

        # If publisher matches known data
        if parsed.field_name == 'publisher':
            existing_pub = self._get_existing_value(existing, 'publisher')
            if existing_pub:
                if parsed.value.lower() == existing_pub.lower():
                    return 1.1
                elif parsed.value.lower() in existing_pub.lower():
                    return 1.0
                else:
                    return 0.8

        return 1.0

    def _validate_value(
        self,
        field_name: str,
        value: Any,
        existing_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Validate a field value.

        Args:
            field_name: Name of field
            value: Value to validate
            existing_metadata: Existing book metadata for context

        Returns:
            Tuple of (is_valid, message)
        """
        if value is None:
            return False, "Value is None"

        # ISBN validation - reject for pre-1970 books (ISBNs didn't exist)
        if field_name in ('isbn_10', 'isbn_13'):
            if existing_metadata:
                pub_year = self._get_existing_value(existing_metadata, 'publication_year')
                if pub_year:
                    try:
                        year = int(pub_year)
                        if year < 1970:
                            return False, f"ISBN not applicable for {year} publication (ISBNs introduced 1970)"
                    except (ValueError, TypeError):
                        pass

        if field_name in ('isbn_10',):
            if not isinstance(value, str) or len(value) != 10:
                return False, f"Invalid ISBN-10 format: {value}"

        if field_name in ('isbn_13',):
            if not isinstance(value, str) or len(value) != 13:
                return False, f"Invalid ISBN-13 format: {value}"

        if field_name == 'page_count':
            try:
                pages = int(value)
                if pages < 10 or pages > 5000:
                    return False, f"Unreasonable page count: {pages}"
            except (ValueError, TypeError):
                return False, f"Invalid page count: {value}"

        if field_name == 'publication_year':
            try:
                year = int(value)
                if year < 1800 or year > 2030:
                    return False, f"Unreasonable year: {year}"
            except (ValueError, TypeError):
                return False, f"Invalid year: {value}"

        return True, "Valid"

    def _generate_reasoning(
        self,
        parsed: ParsedField,
        confidence: float,
        auto_accept: bool
    ) -> str:
        """Generate human-readable reasoning for a match.

        Args:
            parsed: Parsed field
            confidence: Calculated confidence
            auto_accept: Whether auto-accepted

        Returns:
            Reasoning string
        """
        parts = []

        confidence_pct = int(confidence * 100)
        parts.append(f"{confidence_pct}% confidence")

        source_desc = {
            'ebay': 'eBay listing',
            'abebooks': 'AbeBooks',
            'amazon': 'Amazon',
            'worldcat': 'WorldCat',
            'json': 'structured data',
            'text': 'text extraction',
        }.get(parsed.source_type, parsed.source_type)

        parts.append(f"from {source_desc}")

        if auto_accept:
            parts.append("(auto-accepted)")

        return " ".join(parts)

    def _get_existing_value(
        self,
        metadata: Dict[str, Any],
        field_name: str
    ) -> Optional[Any]:
        """Get existing value for a field from metadata.

        Handles nested paths like 'publication_details.publisher'.

        Args:
            metadata: Metadata dict
            field_name: Field name (may include dots for nested)

        Returns:
            Value or None
        """
        # Direct lookup first
        if field_name in metadata:
            return metadata[field_name]

        # Common nested paths
        nested_paths = {
            'publisher': ['publication_details.publisher', 'publisher'],
            'publication_year': ['publication_details.publication_year', 'publication_year'],
            'page_count': ['publication_details.page_count', 'page_count'],
            'isbn_10': ['publication_details.isbn_10', 'isbn_10', 'isbn'],
            'isbn_13': ['publication_details.isbn_13', 'isbn_13', 'isbn'],
            'genre': ['publication_details.genre', 'genre'],
            'binding': ['physical_details.binding_type', 'binding_type', 'binding'],
            'place_of_publication': ['publication_details.place_of_publication', 'place_of_publication'],
        }

        paths = nested_paths.get(field_name, [field_name])
        for path in paths:
            value = self._get_nested(metadata, path)
            if value is not None:
                return value

        return None

    def _get_nested(self, data: Dict, path: str) -> Optional[Any]:
        """Get nested value using dot notation.

        Args:
            data: Dictionary
            path: Dot-separated path

        Returns:
            Value or None
        """
        keys = path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value

    def _identify_missing(self, metadata: Dict[str, Any]) -> List[str]:
        """Identify missing fields in metadata.

        Args:
            metadata: Current metadata

        Returns:
            List of missing field names
        """
        required_fields = [
            'publisher',
            'place_of_publication',
            'isbn_10',
            'isbn_13',
            'page_count',
            'publication_year',
            'genre',
            'binding',
        ]

        missing = []
        for field in required_fields:
            if self._get_existing_value(metadata, field) is None:
                missing.append(field)

        return missing

    def apply_matches(
        self,
        metadata: Dict[str, Any],
        matches: Dict[str, FieldMatch]
    ) -> Dict[str, Any]:
        """Apply accepted matches to metadata.

        Only applies matches that are auto-accepted or user-accepted.

        Args:
            metadata: Current metadata dict
            matches: Dict of field matches

        Returns:
            Updated metadata dict
        """
        result = dict(metadata)

        for field_name, match in matches.items():
            if not match.auto_accepted and not match.user_accepted:
                continue

            # Use user-modified value if available
            value = match.user_modified_value or match.value

            # Apply to appropriate nested location
            result = self._set_field_value(result, field_name, value)

        return result

    def _set_field_value(
        self,
        metadata: Dict[str, Any],
        field_name: str,
        value: Any
    ) -> Dict[str, Any]:
        """Set a field value in metadata, handling nesting.

        Args:
            metadata: Metadata dict
            field_name: Field name
            value: Value to set

        Returns:
            Updated metadata
        """
        # Field to nested path mapping
        field_paths = {
            'publisher': 'publication_details.publisher',
            'place_of_publication': 'publication_details.place_of_publication',
            'publication_year': 'publication_details.publication_year',
            'page_count': 'publication_details.page_count',
            'isbn_10': 'publication_details.isbn_10',
            'isbn_13': 'publication_details.isbn_13',
            'genre': 'publication_details.genre',
            'binding': 'physical_details.binding_type',
        }

        path = field_paths.get(field_name, field_name)
        parts = path.split('.')

        # Navigate/create nested structure
        current = metadata
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set value
        current[parts[-1]] = value

        return metadata


def merge_matches_to_metadata(
    metadata: Dict[str, Any],
    match_result: MatchResult
) -> Dict[str, Any]:
    """Convenience function to merge match results into metadata.

    Args:
        metadata: Current metadata
        match_result: MatchResult from field matching

    Returns:
        Updated metadata with accepted matches applied
    """
    matcher = FieldMatcher()
    return matcher.apply_matches(metadata, match_result.matches)
