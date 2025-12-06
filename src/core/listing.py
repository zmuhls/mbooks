"""Listing model and manager for book inventory."""

import json
import os
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
import uuid


@dataclass
class CopyIdentifier:
    """Identifier for limited edition copies."""
    type: str  # numbered, lettered, none
    value: str


@dataclass
class Dimensions:
    """Physical dimensions of the book."""
    height_cm: Optional[float] = None
    width_cm: Optional[float] = None
    depth_cm: Optional[float] = None
    weight_g: Optional[float] = None


@dataclass
class Listing:
    """Represents a single book listing with full metadata."""

    # Core identification
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    directory: str = ""
    schema_version: str = "1.0"
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    # Basic info
    title: str = ""
    subtitle: Optional[str] = None
    author: Optional[str] = None
    editor: Optional[str] = None
    illustrator: Optional[str] = None
    contributors: List[str] = field(default_factory=list)

    # Publication details
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    original_publication_year: Optional[int] = None
    language: str = "en"
    page_count: Optional[int] = None
    genre: Optional[str] = None

    # Edition details
    edition_description: Optional[str] = None
    is_limited_edition: bool = False
    edition_size: Optional[int] = None
    copy_number: Optional[str] = None
    copy_type: str = "none"  # numbered, lettered, none
    is_signed: bool = False
    signed_by: Optional[str] = None
    signature_notes: Optional[str] = None

    # Physical details
    format: str = "Hardcover"
    binding_type: Optional[str] = None
    binding_color: Optional[str] = None
    gilt_details: Optional[str] = None
    has_dust_jacket: bool = False
    dust_jacket_condition: Optional[str] = None
    has_slipcase: bool = False
    slipcase_condition: Optional[str] = None
    dimensions: Dimensions = field(default_factory=Dimensions)

    # Condition
    overall_grade: Optional[str] = None
    book_condition: Optional[str] = None
    defects: List[str] = field(default_factory=list)
    special_features: List[str] = field(default_factory=list)
    condition_notes: Optional[str] = None

    # Images
    image_files: List[str] = field(default_factory=list)
    primary_image: Optional[str] = None
    image_notes: Dict[str, str] = field(default_factory=dict)

    # Pricing
    price: Optional[float] = None
    estimated_value_min: Optional[float] = None
    estimated_value_max: Optional[float] = None
    pricing_notes: Optional[str] = None

    # eBay specific
    ebay_listing_id: Optional[str] = None
    ebay_category_id: str = "377"
    ebay_title: Optional[str] = None
    ebay_description: Optional[str] = None

    # Notes
    notes: Optional[str] = None
    internal_notes: Optional[str] = None

    # Data tracking
    data_sources: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_metadata_json(cls, json_path: Path) -> 'Listing':
        """Load listing from metadata.json file."""
        with open(json_path, 'r') as f:
            data = json.load(f)

        listing = cls()
        listing.directory = json_path.parent.name

        # Map nested structure to flat attributes
        basic = data.get('basic_info', {})
        listing.title = basic.get('title', '')
        listing.subtitle = basic.get('subtitle')
        listing.author = cls._stringify(basic.get('author'))
        listing.editor = cls._stringify(basic.get('editor'))
        listing.illustrator = basic.get('illustrator')
        listing.contributors = basic.get('contributors', [])

        pub = data.get('publication_details', {})
        listing.isbn_10 = pub.get('isbn_10')
        listing.isbn_13 = pub.get('isbn_13')
        listing.publisher = pub.get('publisher')
        listing.publication_year = pub.get('publication_year')
        listing.original_publication_year = pub.get('original_publication_year')
        listing.language = pub.get('language', 'en')
        listing.page_count = pub.get('page_count')
        listing.genre = cls._stringify(pub.get('genre'))

        edition = data.get('edition_details', {})
        listing.edition_description = edition.get('edition_description')
        listing.is_limited_edition = edition.get('is_limited_edition', False)
        listing.edition_size = edition.get('edition_size')
        copy_id = edition.get('copy_identifier')
        if copy_id:
            listing.copy_type = copy_id.get('type', 'none')
            listing.copy_number = copy_id.get('value')
        listing.is_signed = edition.get('is_signed', False)
        listing.signed_by = cls._stringify(edition.get('signed_by'))
        listing.signature_notes = edition.get('signature_notes')

        physical = data.get('physical_details', {})
        listing.format = physical.get('format', 'Hardcover')
        listing.binding_type = physical.get('binding_type')
        listing.binding_color = physical.get('binding_color')
        listing.gilt_details = physical.get('gilt_details')
        listing.has_dust_jacket = physical.get('has_dust_jacket', False)
        listing.dust_jacket_condition = physical.get('dust_jacket_condition')
        listing.has_slipcase = physical.get('has_slipcase', False)
        listing.slipcase_condition = physical.get('slipcase_condition')

        dims = physical.get('dimensions', {})
        listing.dimensions = Dimensions(
            height_cm=dims.get('height_cm'),
            width_cm=dims.get('width_cm'),
            depth_cm=dims.get('depth_cm'),
            weight_g=dims.get('weight_g')
        )

        condition = data.get('condition', {})
        listing.overall_grade = condition.get('overall_grade')
        listing.book_condition = condition.get('book_condition')
        listing.defects = condition.get('defects', [])
        listing.special_features = condition.get('special_features', [])
        listing.condition_notes = condition.get('condition_notes')

        images = data.get('images', {})
        listing.image_files = images.get('files', [])
        listing.primary_image = images.get('primary_image')
        listing.image_notes = images.get('image_notes', {})

        pricing = data.get('pricing', {})
        listing.estimated_value_min = pricing.get('estimated_value_min')
        listing.estimated_value_max = pricing.get('estimated_value_max')
        listing.pricing_notes = pricing.get('pricing_notes')

        ebay_data = data.get('ebay_listing_data', {})
        listing.ebay_category_id = ebay_data.get('category_id', '377')
        listing.ebay_title = ebay_data.get('listing_title')
        listing.ebay_description = ebay_data.get('listing_description')

        listing.notes = data.get('notes')
        listing.internal_notes = data.get('internal_notes')
        listing.data_sources = data.get('data_sources', {})
        listing.last_updated = data.get('last_updated', datetime.now().isoformat())
        listing.schema_version = data.get('schema_version', '1.0')

        return listing

    @staticmethod
    def _stringify(value) -> Optional[str]:
        """Convert list or string to string."""
        if value is None:
            return None
        if isinstance(value, list):
            return ', '.join(str(v) for v in value)
        return str(value)

    def to_metadata_dict(self) -> Dict[str, Any]:
        """Convert to metadata.json structure."""
        return {
            "schema_version": self.schema_version,
            "last_updated": self.last_updated,
            "basic_info": {
                "title": self.title,
                "subtitle": self.subtitle,
                "author": self.author,
                "editor": self.editor,
                "illustrator": self.illustrator,
                "contributors": self.contributors
            },
            "publication_details": {
                "isbn_10": self.isbn_10,
                "isbn_13": self.isbn_13,
                "publisher": self.publisher,
                "publication_year": self.publication_year,
                "original_publication_year": self.original_publication_year,
                "language": self.language,
                "page_count": self.page_count,
                "genre": self.genre
            },
            "edition_details": {
                "edition_description": self.edition_description,
                "is_limited_edition": self.is_limited_edition,
                "edition_size": self.edition_size,
                "copy_identifier": {
                    "type": self.copy_type,
                    "value": self.copy_number
                } if self.copy_number else None,
                "is_signed": self.is_signed,
                "signed_by": self.signed_by,
                "signature_notes": self.signature_notes
            },
            "physical_details": {
                "format": self.format,
                "binding_type": self.binding_type,
                "binding_color": self.binding_color,
                "gilt_details": self.gilt_details,
                "has_dust_jacket": self.has_dust_jacket,
                "dust_jacket_condition": self.dust_jacket_condition,
                "has_slipcase": self.has_slipcase,
                "slipcase_condition": self.slipcase_condition,
                "dimensions": asdict(self.dimensions)
            },
            "condition": {
                "overall_grade": self.overall_grade,
                "book_condition": self.book_condition,
                "defects": self.defects,
                "special_features": self.special_features,
                "condition_notes": self.condition_notes
            },
            "images": {
                "files": self.image_files,
                "primary_image": self.primary_image,
                "image_notes": self.image_notes
            },
            "pricing": {
                "estimated_value_min": self.estimated_value_min,
                "estimated_value_max": self.estimated_value_max,
                "pricing_notes": self.pricing_notes
            },
            "ebay_listing_data": {
                "category_id": self.ebay_category_id,
                "listing_title": self.ebay_title,
                "listing_description": self.ebay_description
            },
            "notes": self.notes,
            "internal_notes": self.internal_notes,
            "data_sources": self.data_sources
        }

    def save(self, base_path: Path):
        """Save listing to metadata.json."""
        self.last_updated = datetime.now().isoformat()
        listing_path = base_path / self.directory
        listing_path.mkdir(parents=True, exist_ok=True)

        metadata_path = listing_path / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(self.to_metadata_dict(), f, indent=2)

    def generate_ebay_title(self) -> str:
        """Generate optimized 80-character eBay title."""
        parts = [self.title]

        if self.author:
            parts.append(f"by {self.author.split(',')[0]}")
        elif self.editor:
            parts.append(f"Ed. {self.editor.split(',')[0]}")

        if self.is_signed and self.signed_by:
            parts.append(f"SIGNED")

        if self.is_limited_edition:
            parts.append("Limited Ed")

        if self.has_slipcase:
            parts.append("w/Slipcase")

        title = " ".join(parts)
        return title[:77] + "..." if len(title) > 80 else title

    def get_special_attributes(self) -> List[str]:
        """Get list of special attributes for eBay."""
        attrs = []
        if self.is_signed:
            attrs.append("Signed")
        if self.is_limited_edition:
            attrs.append("Limited Edition")
        if self.has_dust_jacket:
            attrs.append("Dust Jacket")
        if self.has_slipcase:
            attrs.append("Slipcase")
        if self.binding_type == "Leather":
            attrs.append("Leather Bound")
        return attrs

    @property
    def creator(self) -> str:
        """Get primary creator (author or editor)."""
        return self.author or self.editor or "Unknown"

    @property
    def image_count(self) -> int:
        """Get number of images."""
        return len(self.image_files)


class ListingManager:
    """Manages collection of book listings."""

    def __init__(self, listings_path: Path):
        self.listings_path = Path(listings_path)
        self._listings: Dict[str, Listing] = {}
        self._load_all()

    def _load_all(self):
        """Load all listings from disk."""
        if not self.listings_path.exists():
            return

        for item in self.listings_path.iterdir():
            if item.is_dir():
                metadata_path = item / "metadata.json"
                if metadata_path.exists():
                    try:
                        listing = Listing.from_metadata_json(metadata_path)
                        self._listings[item.name] = listing
                    except Exception as e:
                        print(f"Error loading {item.name}: {e}")

    def reload(self):
        """Reload all listings from disk."""
        self._listings.clear()
        self._load_all()

    @property
    def all(self) -> List[Listing]:
        """Get all listings."""
        return list(self._listings.values())

    def get(self, directory: str) -> Optional[Listing]:
        """Get listing by directory name."""
        return self._listings.get(directory)

    def add(self, listing: Listing):
        """Add or update a listing."""
        self._listings[listing.directory] = listing
        listing.save(self.listings_path)

    def remove(self, directory: str) -> bool:
        """Remove a listing."""
        if directory in self._listings:
            del self._listings[directory]
            return True
        return False

    def filter(self, signed: Optional[bool] = None,
               limited: Optional[bool] = None,
               search: Optional[str] = None) -> List[Listing]:
        """Filter listings by criteria."""
        results = self.all

        if signed is not None:
            results = [l for l in results if l.is_signed == signed]

        if limited is not None:
            results = [l for l in results if l.is_limited_edition == limited]

        if search:
            search_lower = search.lower()
            results = [l for l in results if
                       search_lower in l.title.lower() or
                       (l.author and search_lower in l.author.lower()) or
                       (l.editor and search_lower in l.editor.lower())]

        return results

    @property
    def count(self) -> int:
        """Get total number of listings."""
        return len(self._listings)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        listings = self.all
        return {
            "total": len(listings),
            "signed": len([l for l in listings if l.is_signed]),
            "limited_edition": len([l for l in listings if l.is_limited_edition]),
            "with_slipcase": len([l for l in listings if l.has_slipcase]),
            "with_dust_jacket": len([l for l in listings if l.has_dust_jacket]),
            "total_images": sum(l.image_count for l in listings)
        }
