"""
Metadata Migrator

Converts old flat metadata format to new comprehensive schema format.
Preserves all existing data while adding structure for eBay integration.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Union


class MetadataMigrator:
    """Convert old metadata format to new structured schema"""

    def __init__(self):
        self.schema_version = "1.0"

    def migrate(self, old_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert old flat metadata to new structured format

        Args:
            old_metadata: Original metadata dictionary

        Returns:
            New metadata dictionary conforming to schema
        """
        new_metadata = self._init_empty_schema()
        new_metadata['schema_version'] = self.schema_version
        new_metadata['last_updated'] = datetime.now().isoformat()

        # Migrate each section
        self._migrate_basic_info(old_metadata, new_metadata)
        self._migrate_publication_details(old_metadata, new_metadata)
        self._migrate_edition_details(old_metadata, new_metadata)
        self._migrate_physical_details(old_metadata, new_metadata)
        self._migrate_condition(old_metadata, new_metadata)
        self._migrate_images(old_metadata, new_metadata)

        # Preserve notes
        new_metadata['notes'] = old_metadata.get('notes', None)

        # Track data sources - all migrated fields are manual entry
        new_metadata['data_sources']['manual_entry'] = list(old_metadata.keys())

        return new_metadata

    def _init_empty_schema(self) -> Dict[str, Any]:
        """Initialize metadata structure with empty/default values"""
        return {
            "schema_version": "",
            "last_updated": "",
            "basic_info": {
                "title": "",
                "subtitle": None,
                "author": None,
                "editor": None,
                "illustrator": None,
                "contributors": []
            },
            "publication_details": {
                "isbn_10": None,
                "isbn_13": None,
                "publisher": None,
                "publication_year": None,
                "original_publication_year": None,
                "language": "en",
                "page_count": None,
                "genre": None
            },
            "edition_details": {
                "edition_description": None,
                "is_limited_edition": False,
                "edition_size": None,
                "copy_identifier": None,
                "is_signed": False,
                "signed_by": None,
                "signature_notes": None
            },
            "physical_details": {
                "format": None,
                "binding_type": None,
                "binding_color": None,
                "gilt_details": None,
                "has_dust_jacket": False,
                "dust_jacket_condition": None,
                "has_slipcase": False,
                "slipcase_condition": None,
                "dimensions": {
                    "height_cm": None,
                    "width_cm": None,
                    "depth_cm": None,
                    "weight_g": None
                }
            },
            "condition": {
                "overall_grade": None,
                "book_condition": None,
                "defects": [],
                "special_features": [],
                "condition_notes": None
            },
            "images": {
                "files": [],
                "primary_image": None,
                "image_notes": {}
            },
            "pricing": {
                "estimated_value_min": None,
                "estimated_value_max": None,
                "comparable_sales": [],
                "pricing_notes": None
            },
            "ebay_listing_data": {
                "category_id": None,
                "category_path": None,
                "listing_title": None,
                "listing_description": None,
                "product_identifiers": {
                    "epid": None,
                    "upc": None,
                    "ean": None
                },
                "item_specifics": {
                    "Format": None,
                    "Language": None,
                    "Author": None,
                    "Publisher": None,
                    "Publication Year": None,
                    "Special Attributes": []
                },
                "policies": {
                    "payment_policy_id": None,
                    "return_policy_id": None,
                    "fulfillment_policy_id": None
                }
            },
            "data_sources": {
                "manual_entry": [],
                "vision_extracted": [],
                "api_enriched": {
                    "source": None,
                    "fields": [],
                    "retrieved_at": None
                }
            },
            "notes": None,
            "internal_notes": None
        }

    def _migrate_basic_info(self, old: Dict[str, Any], new: Dict[str, Any]) -> None:
        """Migrate basic identifying information"""
        basic_info = new['basic_info']

        # Title is required
        basic_info['title'] = old.get('title', '')
        basic_info['subtitle'] = old.get('subtitle', None)
        basic_info['author'] = old.get('author', None)
        basic_info['editor'] = old.get('editor', None)
        basic_info['illustrator'] = old.get('illustrator', None)

        # Contributors - leave empty for now, can be manually added later
        basic_info['contributors'] = []

    def _migrate_publication_details(self, old: Dict[str, Any], new: Dict[str, Any]) -> None:
        """Migrate publication-specific information"""
        pub_details = new['publication_details']

        # ISBN - currently not in old metadata
        pub_details['isbn_10'] = None
        pub_details['isbn_13'] = None

        # Publisher
        pub_details['publisher'] = old.get('publisher', None)

        # Publication year - leave for API enrichment
        pub_details['publication_year'] = None
        pub_details['original_publication_year'] = None

        # Language - default to English, can be overridden
        pub_details['language'] = "en"

        # Page count and genre - leave for enrichment
        pub_details['page_count'] = None
        pub_details['genre'] = None

    def _migrate_edition_details(self, old: Dict[str, Any], new: Dict[str, Any]) -> None:
        """Migrate edition and collectibility information"""
        edition_details = new['edition_details']

        # Edition description
        edition_details['edition_description'] = old.get('edition', None)

        # Handle copy identifiers (numbered or lettered)
        if 'copy_number' in old:
            edition_details['is_limited_edition'] = True
            edition_details['copy_identifier'] = {
                'type': 'numbered',
                'value': str(old['copy_number'])
            }

            # Try to extract edition size from edition description
            edition_text = old.get('edition', '')
            edition_size = self._extract_edition_size(edition_text)
            if edition_size:
                edition_details['edition_size'] = edition_size

        elif 'copy_letter' in old:
            edition_details['is_limited_edition'] = True
            edition_details['copy_identifier'] = {
                'type': 'lettered',
                'value': old['copy_letter']
            }

            # Lettered editions are typically 26 or 52 copies
            edition_details['edition_size'] = self._guess_lettered_edition_size(
                old['copy_letter']
            )

        # Handle signatures
        if 'signed_by' in old:
            edition_details['is_signed'] = True
            edition_details['signed_by'] = old['signed_by']
        elif 'signed' in old:
            edition_details['is_signed'] = True
            # Parse signature notes
            signed_value = old['signed']
            if isinstance(signed_value, str):
                edition_details['signature_notes'] = signed_value
            elif isinstance(signed_value, bool) and signed_value:
                edition_details['signature_notes'] = "Signed edition"

    def _migrate_physical_details(self, old: Dict[str, Any], new: Dict[str, Any]) -> None:
        """Migrate physical characteristics"""
        physical_details = new['physical_details']

        # Format
        format_value = old.get('format', '')
        physical_details['format'] = self._standardize_format(format_value)

        # Extract binding and other details from format and notes
        notes = old.get('notes', '')

        # Binding type and color from notes
        binding_info = self._extract_binding_info(notes)
        physical_details['binding_type'] = binding_info['type']
        physical_details['binding_color'] = binding_info['color']
        physical_details['gilt_details'] = binding_info['gilt']

        # Dust jacket and slipcase
        if 'dust jacket' in notes.lower() or 'dj' in notes.lower():
            physical_details['has_dust_jacket'] = True
        if 'slipcase' in notes.lower() or 'slip case' in notes.lower() or 'with slipcase' in format_value.lower():
            physical_details['has_slipcase'] = True

    def _migrate_condition(self, old: Dict[str, Any], new: Dict[str, Any]) -> None:
        """Migrate condition information"""
        condition = new['condition']

        # If condition explicitly stated, use it
        if 'condition' in old:
            old_condition = old['condition']
            condition['overall_grade'] = self._standardize_condition(old_condition)
            condition['condition_notes'] = f"Condition: {old_condition}"
        else:
            # For collectible limited editions, assume good condition unless stated
            # Leave for vision analysis to determine
            condition['overall_grade'] = None

    def _migrate_images(self, old: Dict[str, Any], new: Dict[str, Any]) -> None:
        """Migrate image information"""
        images = new['images']

        # Copy image files list
        if 'images' in old:
            images['files'] = old['images'] if isinstance(old['images'], list) else []

            # Set first image as primary
            if images['files']:
                images['primary_image'] = images['files'][0]

    # Helper methods

    def _extract_edition_size(self, edition_text: str) -> Union[int, None]:
        """Extract edition size from text like 'Limited to 500 numbered copies'"""
        if not edition_text:
            return None

        # Look for patterns like "Limited to X copies" or "X numbered copies"
        patterns = [
            r'Limited to (\d+)',
            r'limited to (\d+)',
            r'(\d+) numbered copies',
            r'(\d+) lettered copies',
            r'edition of (\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, edition_text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def _guess_lettered_edition_size(self, letter: str) -> Union[int, None]:
        """Guess edition size based on lettered identifier"""
        # Single letters typically mean 26 copies (A-Z)
        # Double letters typically mean 52 copies (AA-ZZ)
        if len(letter) == 1:
            return 26
        elif len(letter) == 2:
            return 52
        return None

    def _standardize_format(self, format_value: str) -> Union[str, None]:
        """Standardize format to schema enum values"""
        if not format_value:
            return None

        format_lower = format_value.lower()

        if 'hardcover' in format_lower or 'hardbound' in format_lower:
            return "Hardcover"
        elif 'leather' in format_lower:
            return "Leather Bound"
        elif 'paperback' in format_lower:
            if 'trade' in format_lower:
                return "Trade Paperback"
            elif 'mass market' in format_lower:
                return "Mass Market Paperback"
            return "Paperback"

        # If can't determine, return original
        return format_value if format_value else None

    def _extract_binding_info(self, notes: str) -> Dict[str, Union[str, None]]:
        """Extract binding type, color, and gilt details from notes"""
        binding_info = {
            'type': None,
            'color': None,
            'gilt': None
        }

        if not notes:
            return binding_info

        notes_lower = notes.lower()

        # Binding type
        if 'leather' in notes_lower:
            if 'half-leather' in notes_lower or 'half leather' in notes_lower:
                binding_info['type'] = "Half-Leather"
            elif 'full leather' in notes_lower:
                binding_info['type'] = "Full Leather"
            else:
                binding_info['type'] = "Leather"
        elif 'cloth' in notes_lower:
            binding_info['type'] = "Cloth"

        # Colors (common ones)
        colors = ['red', 'orange', 'brown', 'black', 'blue', 'green', 'tan', 'burgundy', 'maroon']
        for color in colors:
            if color in notes_lower:
                binding_info['color'] = color.capitalize()
                break

        # Gilt details
        if 'gilt' in notes_lower:
            # Extract gilt-related text
            gilt_patterns = [
                r'(gold gilt [^,\.]+)',
                r'(gilt [^,\.]+)',
                r'([^,\.]+ gilt[^,\.]*)'
            ]
            for pattern in gilt_patterns:
                match = re.search(pattern, notes_lower)
                if match:
                    binding_info['gilt'] = match.group(1).strip().capitalize()
                    break

        return binding_info

    def _standardize_condition(self, condition_str: str) -> str:
        """Standardize condition to eBay enum values"""
        condition_lower = condition_str.lower()

        if 'new' in condition_lower or 'mint' in condition_lower:
            if 'like' in condition_lower:
                return "LIKE_NEW"
            return "NEW"
        elif 'excellent' in condition_lower or 'fine' in condition_lower:
            return "VERY_GOOD"
        elif 'very good' in condition_lower:
            return "VERY_GOOD"
        elif 'good' in condition_lower:
            return "GOOD"
        elif 'acceptable' in condition_lower or 'fair' in condition_lower:
            return "ACCEPTABLE"

        # Default to VERY_GOOD for collectibles unless stated otherwise
        return "VERY_GOOD"


def validate_migration(old_metadata: Dict[str, Any], new_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that migration didn't lose data

    Returns:
        Dict with validation results
    """
    old_fields = set(old_metadata.keys())
    tracked_fields = set(new_metadata['data_sources']['manual_entry'])

    missing_fields = old_fields - tracked_fields

    return {
        'success': len(missing_fields) == 0,
        'old_field_count': len(old_fields),
        'tracked_field_count': len(tracked_fields),
        'missing_fields': list(missing_fields)
    }
