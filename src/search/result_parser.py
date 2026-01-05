"""Parse search results into structured metadata fields.

Extracts bibliographic data, pricing information, and condition language
from search results across different sources.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class ParsedField:
    """Represents a parsed metadata field from search results."""
    field_name: str
    value: Any
    confidence: float  # 0.0 - 1.0
    source: str  # URL or source identifier
    source_type: str  # 'ebay', 'abebooks', 'amazon', etc.
    raw_text: str  # Original text this was extracted from


@dataclass
class PricingData:
    """Represents comparable pricing data."""
    min_price: Optional[float]
    max_price: Optional[float]
    avg_price: Optional[float]
    recent_price: Optional[float]
    recent_date: Optional[str]
    num_sales: int
    source_listings: List[Dict[str, Any]]


class SearchResultParser:
    """Parse and normalize search results into structured data."""

    # Patterns for extracting data
    ISBN_10_PATTERN = re.compile(r'\b(\d{9}[\dX])\b')
    ISBN_13_PATTERN = re.compile(r'\b(97[89]\d{10})\b')
    PRICE_PATTERN = re.compile(r'\$[\d,]+\.?\d*')
    YEAR_PATTERN = re.compile(r'\b(19\d{2}|20[0-2]\d)\b')
    PAGE_COUNT_PATTERN = re.compile(r'(\d{2,4})\s*(?:pages?|pp\.?|p\.)', re.IGNORECASE)

    # Publisher patterns (common collectible publishers)
    KNOWN_PUBLISHERS = [
        'Cemetery Dance', 'Subterranean Press', 'Suntup Editions',
        'B.E. Trice', 'Mark V. Ziesing', 'Mark Ziesing', 'Centipede Press',
        'PS Publishing', 'Gauntlet Press', 'Donald M. Grant', 'Easton Press',
        'Charnel House', 'Dark Regions Press', 'Night Shade Books',
        'Limited Editions Club', 'Folio Society', 'Franklin Library',
        "Hill House Publishers", 'Phantasia Press', 'Scream Press',
    ]

    def __init__(self):
        """Initialize the parser."""
        self.parsed_fields: List[ParsedField] = []

    def parse_synthesized_answer(
        self,
        text: str,
        source: str = 'perplexity'
    ) -> List[ParsedField]:
        """Parse Perplexity's synthesized answer for structured data.

        Args:
            text: Synthesized answer text
            source: Source identifier

        Returns:
            List of parsed fields
        """
        fields = []

        # Try to extract JSON if present
        json_data = self._extract_json(text)
        if json_data:
            fields.extend(self._parse_json_response(json_data, source))

        # Also parse free text for additional fields
        fields.extend(self._parse_free_text(text, source))

        # Deduplicate, keeping highest confidence
        return self._deduplicate_fields(fields)

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON object from text.

        Args:
            text: Text that may contain JSON

        Returns:
            Parsed JSON dict or None
        """
        # Try to find JSON in code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON object
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        return None

    def _parse_json_response(
        self,
        data: Dict,
        source: str
    ) -> List[ParsedField]:
        """Parse structured JSON response.

        Args:
            data: JSON data dict
            source: Source identifier

        Returns:
            List of parsed fields
        """
        fields = []

        # Map common JSON keys to our field names
        field_map = {
            'publisher': 'publisher',
            'publisher_name': 'publisher',
            'place_of_publication': 'place_of_publication',
            'publication_place': 'place_of_publication',
            'location': 'place_of_publication',
            'isbn': 'isbn',
            'isbn_10': 'isbn_10',
            'isbn_13': 'isbn_13',
            'isbn-10': 'isbn_10',
            'isbn-13': 'isbn_13',
            'pages': 'page_count',
            'page_count': 'page_count',
            'num_pages': 'page_count',
            'year': 'publication_year',
            'publication_year': 'publication_year',
            'genre': 'genre',
            'subject': 'genre',
            'binding': 'binding',
            'format': 'binding',
        }

        for json_key, field_name in field_map.items():
            if json_key in data and data[json_key]:
                value = data[json_key]
                fields.append(ParsedField(
                    field_name=field_name,
                    value=value,
                    confidence=0.90,  # High confidence for structured data
                    source=source,
                    source_type='json',
                    raw_text=str(value)
                ))

        return fields

    def _parse_free_text(self, text: str, source: str) -> List[ParsedField]:
        """Parse free-form text for metadata.

        Args:
            text: Text to parse
            source: Source identifier

        Returns:
            List of parsed fields
        """
        fields = []

        # ISBN-10
        isbn10_matches = self.ISBN_10_PATTERN.findall(text)
        for isbn in isbn10_matches:
            if self._validate_isbn10(isbn):
                fields.append(ParsedField(
                    field_name='isbn_10',
                    value=isbn,
                    confidence=0.95,
                    source=source,
                    source_type='text',
                    raw_text=isbn
                ))
                break

        # ISBN-13
        isbn13_matches = self.ISBN_13_PATTERN.findall(text)
        for isbn in isbn13_matches:
            if self._validate_isbn13(isbn):
                fields.append(ParsedField(
                    field_name='isbn_13',
                    value=isbn,
                    confidence=0.95,
                    source=source,
                    source_type='text',
                    raw_text=isbn
                ))
                break

        # Page count
        page_matches = self.PAGE_COUNT_PATTERN.findall(text)
        if page_matches:
            # Take first reasonable page count
            for pages in page_matches:
                pages_int = int(pages)
                if 10 < pages_int < 2000:
                    fields.append(ParsedField(
                        field_name='page_count',
                        value=pages_int,
                        confidence=0.80,
                        source=source,
                        source_type='text',
                        raw_text=pages
                    ))
                    break

        # Known publishers
        text_lower = text.lower()
        for publisher in self.KNOWN_PUBLISHERS:
            if publisher.lower() in text_lower:
                # Try to extract location too
                location = self._extract_publisher_location(text, publisher)
                fields.append(ParsedField(
                    field_name='publisher',
                    value=publisher,
                    confidence=0.90,
                    source=source,
                    source_type='text',
                    raw_text=publisher
                ))
                if location:
                    fields.append(ParsedField(
                        field_name='place_of_publication',
                        value=location,
                        confidence=0.85,
                        source=source,
                        source_type='text',
                        raw_text=location
                    ))
                break

        return fields

    def _extract_publisher_location(
        self,
        text: str,
        publisher: str
    ) -> Optional[str]:
        """Extract publisher location from text.

        Args:
            text: Full text
            publisher: Publisher name found

        Returns:
            Location string or None
        """
        # Common publisher locations
        known_locations = {
            'Cemetery Dance': 'Forest Hill, MD',
            'Subterranean Press': 'Burton, MI',
            'Suntup Editions': 'Irvine, CA',
            'B.E. Trice': 'New Orleans, LA',
            'Mark V. Ziesing': 'Shingletown, CA',
            'Mark Ziesing': 'Shingletown, CA',
            'Centipede Press': 'Lakewood, CO',
            'PS Publishing': 'Hornsea, UK',
            'Easton Press': 'Norwalk, CT',
            'Charnel House': 'Lynbrook, NY',
            'Night Shade Books': 'San Francisco, CA',
            'Donald M. Grant': 'Hampton Falls, NH',
        }

        if publisher in known_locations:
            return known_locations[publisher]

        # Try to find location patterns near publisher name
        pub_idx = text.lower().find(publisher.lower())
        if pub_idx != -1:
            # Look for ", City, State" pattern nearby
            context = text[pub_idx:pub_idx + 100]
            location_match = re.search(r',\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s*([A-Z]{2})', context)
            if location_match:
                city = location_match.group(1)
                state = location_match.group(2)
                return f"{city}, {state}"

        return None

    def parse_ebay_listing(
        self,
        result_data: Dict[str, Any],
        url: str
    ) -> Tuple[List[ParsedField], Optional[PricingData]]:
        """Parse eBay listing result.

        Args:
            result_data: Raw result data
            url: Listing URL

        Returns:
            Tuple of (parsed fields, pricing data)
        """
        fields = []
        pricing = None

        snippet = result_data.get('snippet', '')
        title = result_data.get('title', '')
        full_text = f"{title} {snippet}"

        # Extract fields from listing
        fields.extend(self._parse_free_text(full_text, url))

        # Extract price if present
        prices = self.PRICE_PATTERN.findall(full_text)
        if prices:
            price_values = [self._parse_price(p) for p in prices]
            price_values = [p for p in price_values if p is not None]
            if price_values:
                pricing = PricingData(
                    min_price=min(price_values),
                    max_price=max(price_values),
                    avg_price=sum(price_values) / len(price_values),
                    recent_price=price_values[0],
                    recent_date=None,
                    num_sales=1,
                    source_listings=[{'url': url, 'price': price_values[0]}]
                )

        return fields, pricing

    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse price string to float.

        Args:
            price_str: Price string like '$99.95'

        Returns:
            Float value or None
        """
        try:
            cleaned = price_str.replace('$', '').replace(',', '')
            return float(cleaned)
        except ValueError:
            return None

    def _validate_isbn10(self, isbn: str) -> bool:
        """Validate ISBN-10 checksum.

        Args:
            isbn: 10-character ISBN string

        Returns:
            True if valid
        """
        if len(isbn) != 10:
            return False

        try:
            total = 0
            for i, char in enumerate(isbn[:-1]):
                total += int(char) * (10 - i)

            check = isbn[-1]
            if check == 'X':
                total += 10
            else:
                total += int(check)

            return total % 11 == 0
        except ValueError:
            return False

    def _validate_isbn13(self, isbn: str) -> bool:
        """Validate ISBN-13 checksum.

        Args:
            isbn: 13-character ISBN string

        Returns:
            True if valid
        """
        if len(isbn) != 13:
            return False

        try:
            total = 0
            for i, char in enumerate(isbn):
                digit = int(char)
                if i % 2 == 0:
                    total += digit
                else:
                    total += digit * 3

            return total % 10 == 0
        except ValueError:
            return False

    def _deduplicate_fields(
        self,
        fields: List[ParsedField]
    ) -> List[ParsedField]:
        """Remove duplicate fields, keeping highest confidence.

        Args:
            fields: List of parsed fields

        Returns:
            Deduplicated list
        """
        by_field: Dict[str, ParsedField] = {}

        for field in fields:
            existing = by_field.get(field.field_name)
            if existing is None or field.confidence > existing.confidence:
                by_field[field.field_name] = field

        return list(by_field.values())

    def aggregate_pricing(
        self,
        pricing_list: List[PricingData]
    ) -> Optional[PricingData]:
        """Aggregate multiple pricing data points.

        Args:
            pricing_list: List of PricingData from different sources

        Returns:
            Aggregated PricingData or None
        """
        if not pricing_list:
            return None

        all_prices = []
        all_listings = []

        for pricing in pricing_list:
            if pricing.recent_price:
                all_prices.append(pricing.recent_price)
            all_listings.extend(pricing.source_listings)

        if not all_prices:
            return None

        return PricingData(
            min_price=min(all_prices),
            max_price=max(all_prices),
            avg_price=sum(all_prices) / len(all_prices),
            recent_price=all_prices[0] if all_prices else None,
            recent_date=None,
            num_sales=len(all_prices),
            source_listings=all_listings
        )
