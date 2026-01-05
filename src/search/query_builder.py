"""Search query builder for book metadata enrichment.

Generates optimized Boolean search queries for different sources:
- eBay completed listings (pricing, condition language, patterns)
- AbeBooks/Amazon (bibliographic details)
- General bibliographic (ISBN, publisher, page count)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class SearchQuery:
    """Represents a generated search query."""
    query_type: str
    query_text: str
    target_fields: List[str]
    priority: int
    source: str  # 'ebay', 'abebooks', 'amazon', 'bibliographic'


class SearchQueryBuilder:
    """Generate optimized search queries from book metadata."""

    # Query templates for different sources
    TEMPLATES = {
        'ebay_completed': {
            'template': 'site:ebay.com "{title}" {edition_tags} {creator}',
            'priority': 1,
            'source': 'ebay',
            'target_fields': [
                'comparable_prices', 'condition_language', 'place_of_publication',
                'publisher', 'item_specifics', 'special_attributes'
            ]
        },
        'ebay_sold': {
            'template': 'site:ebay.com/itm "{title}" sold {edition_tags}',
            'priority': 2,
            'source': 'ebay',
            'target_fields': ['comparable_prices', 'sold_date']
        },
        'abebooks': {
            'template': 'site:abebooks.com "{title}" {author} {edition_type}',
            'priority': 3,
            'source': 'abebooks',
            'target_fields': ['publisher', 'page_count', 'isbn', 'binding']
        },
        'amazon': {
            'template': 'site:amazon.com "{title}" {author} hardcover',
            'priority': 4,
            'source': 'amazon',
            'target_fields': ['isbn', 'page_count', 'publisher', 'dimensions']
        },
        'bibliographic': {
            'template': '"{title}" {author} publisher ISBN {year}',
            'priority': 5,
            'source': 'bibliographic',
            'target_fields': ['isbn_10', 'isbn_13', 'publisher', 'page_count', 'genre']
        },
        'worldcat': {
            'template': 'site:worldcat.org "{title}" {author}',
            'priority': 6,
            'source': 'worldcat',
            'target_fields': ['isbn', 'publisher', 'publication_year', 'page_count']
        },
    }

    def __init__(self, metadata: Dict[str, Any]):
        """Initialize with extracted metadata.

        Args:
            metadata: Extracted book metadata from vision phase
        """
        self.metadata = metadata
        self._extract_key_fields()

    def _extract_key_fields(self):
        """Extract key fields from metadata for query building."""
        # Basic info
        basic = self.metadata.get('basic_info', {})
        self.title = basic.get('title') or self.metadata.get('title', '')
        self.author = basic.get('author') or self.metadata.get('author')
        self.editor = basic.get('editor') or self.metadata.get('editor')

        # Edition details
        edition = self.metadata.get('edition_details', {})
        self.is_signed = edition.get('is_signed') or self.metadata.get('is_signed', False)
        self.is_limited = edition.get('is_limited_edition') or self.metadata.get('is_limited_edition', False)
        self.edition_size = edition.get('edition_size') or self.metadata.get('edition_size')
        self.copy_number = edition.get('copy_identifier', {}).get('value') or self.metadata.get('copy_number')

        # Publication details
        pub = self.metadata.get('publication_details', {})
        self.year = pub.get('publication_year') or self.metadata.get('publication_year')
        self.publisher = pub.get('publisher') or self.metadata.get('publisher')
        self.isbn = pub.get('isbn_10') or pub.get('isbn_13') or self.metadata.get('isbn')

    @property
    def creator(self) -> str:
        """Get the primary creator (author or editor)."""
        if self.author:
            if isinstance(self.author, list):
                return self.author[0]
            return self.author
        if self.editor:
            if isinstance(self.editor, list):
                return self.editor[0]
            return self.editor
        return ''

    @property
    def edition_tags(self) -> str:
        """Build edition descriptor tags for queries."""
        tags = []

        if self.is_signed:
            tags.append('"Signed"')

        if self.is_limited:
            tags.append('"Limited Edition"')
            if self.edition_size:
                tags.append(str(self.edition_size))

        return ' '.join(tags)

    @property
    def edition_type(self) -> str:
        """Get edition type string."""
        if self.is_limited and self.is_signed:
            return 'signed limited edition'
        elif self.is_limited:
            return 'limited edition'
        elif self.is_signed:
            return 'signed'
        return 'first edition'

    def build_query(self, template_name: str) -> Optional[SearchQuery]:
        """Build a single query from a template.

        Args:
            template_name: Name of template to use

        Returns:
            SearchQuery object or None if insufficient data
        """
        if template_name not in self.TEMPLATES:
            return None

        if not self.title:
            return None

        config = self.TEMPLATES[template_name]
        template = config['template']

        # Build substitution values
        subs = {
            'title': self.title,
            'author': self.creator or '',
            'editor': self.editor or '',
            'creator': self.creator or '',
            'edition_tags': self.edition_tags,
            'edition_type': self.edition_type,
            'year': str(self.year) if self.year else '',
            'publisher': self.publisher or '',
            'isbn': self.isbn or '',
        }

        # Apply substitutions
        query_text = template.format(**subs)

        # Clean up extra spaces
        query_text = ' '.join(query_text.split())

        return SearchQuery(
            query_type=template_name,
            query_text=query_text,
            target_fields=config['target_fields'],
            priority=config['priority'],
            source=config['source']
        )

    def build_ebay_query(self) -> Optional[SearchQuery]:
        """Build optimized eBay completed listing query."""
        return self.build_query('ebay_completed')

    def build_bibliographic_query(self) -> Optional[SearchQuery]:
        """Build bibliographic/ISBN lookup query."""
        return self.build_query('bibliographic')

    def get_all_queries(self) -> List[SearchQuery]:
        """Generate all applicable queries for the metadata.

        Returns:
            List of SearchQuery objects sorted by priority
        """
        queries = []

        for template_name in self.TEMPLATES:
            query = self.build_query(template_name)
            if query:
                queries.append(query)

        # Sort by priority (lower = higher priority)
        queries.sort(key=lambda q: q.priority)

        return queries

    def get_queries_for_fields(self, fields: List[str]) -> List[SearchQuery]:
        """Get queries that target specific missing fields.

        Args:
            fields: List of field names to find queries for

        Returns:
            List of SearchQuery objects that target the specified fields
        """
        all_queries = self.get_all_queries()

        matching = []
        for query in all_queries:
            if any(f in query.target_fields for f in fields):
                matching.append(query)

        return matching

    def build_custom_query(
        self,
        source: str = 'ebay',
        include_title: bool = True,
        include_author: bool = True,
        include_edition: bool = True,
        additional_terms: Optional[List[str]] = None
    ) -> str:
        """Build a custom query with fine-grained control.

        Args:
            source: Target source ('ebay', 'abebooks', 'amazon')
            include_title: Whether to include title
            include_author: Whether to include author/editor
            include_edition: Whether to include edition tags
            additional_terms: Additional search terms

        Returns:
            Query string
        """
        parts = []

        # Site restriction
        site_map = {
            'ebay': 'site:ebay.com',
            'abebooks': 'site:abebooks.com',
            'amazon': 'site:amazon.com',
        }
        if source in site_map:
            parts.append(site_map[source])

        # Title
        if include_title and self.title:
            parts.append(f'"{self.title}"')

        # Edition tags
        if include_edition and self.edition_tags:
            parts.append(self.edition_tags)

        # Creator
        if include_author and self.creator:
            parts.append(self.creator)

        # Additional terms
        if additional_terms:
            parts.extend(additional_terms)

        return ' '.join(parts)


def identify_missing_fields(metadata: Dict[str, Any]) -> List[str]:
    """Identify fields that are missing or empty in metadata.

    Args:
        metadata: Current metadata dictionary

    Returns:
        List of field names that need to be populated
    """
    # Fields we want to populate for eBay compliance
    target_fields = {
        'publisher': ['publication_details.publisher', 'publisher'],
        'place_of_publication': ['publication_details.place_of_publication', 'place_of_publication'],
        'isbn': ['publication_details.isbn_10', 'publication_details.isbn_13', 'isbn'],
        'page_count': ['publication_details.page_count', 'page_count'],
        'genre': ['publication_details.genre', 'genre'],
        'topics': ['publication_details.topics', 'topics'],
        'publication_year': ['publication_details.publication_year', 'publication_year'],
        'binding': ['physical_details.binding_type', 'binding_type'],
        'contributors': ['basic_info.contributors', 'contributors'],
    }

    missing = []

    for field_name, paths in target_fields.items():
        found = False
        for path in paths:
            value = _get_nested_value(metadata, path)
            if value:
                found = True
                break
        if not found:
            missing.append(field_name)

    return missing


def _get_nested_value(data: Dict, path: str) -> Any:
    """Get a value from a nested dictionary using dot notation.

    Args:
        data: Dictionary to search
        path: Dot-separated path (e.g., 'publication_details.publisher')

    Returns:
        Value at path or None
    """
    keys = path.split('.')
    value = data

    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None

    return value
