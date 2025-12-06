"""eBay CSV bulk upload exporter."""

import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


class EbayExporter:
    """Export book listings to eBay bulk upload CSV format."""

    # eBay field mappings
    EBAY_FIELDS = [
        'Action', 'CustomLabel', 'Title', 'Category', 'ConditionID',
        'C:Author', 'C:Publisher', 'C:Publication Year', 'C:Format',
        'C:Language', 'C:Signed', 'C:Special Attributes',
        'PicURL', 'Description', 'Format', 'Duration', 'StartPrice',
        'Quantity', 'Location', 'ShippingType', 'ShippingService-1:Option',
        'ShippingService-1:Cost', 'ReturnsAcceptedOption', 'ReturnPolicy'
    ]

    CONDITION_MAP = {
        'NEW': 1000,
        'LIKE_NEW': 2750,
        'VERY_GOOD': 4000,
        'GOOD': 5000,
        'ACCEPTABLE': 6000
    }

    def __init__(self, listings_path: Path):
        self.listings_path = Path(listings_path)

    def load_listings(self) -> List[Dict]:
        """Load all metadata.json files from listings directory."""
        listings = []
        for item_dir in self.listings_path.iterdir():
            if item_dir.is_dir():
                metadata_file = item_dir / 'metadata.json'
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        data = json.load(f)
                        data['_dir'] = item_dir.name
                        listings.append(data)
        return listings

    def generate_title(self, listing: Dict) -> str:
        """Generate eBay-optimized title (80 char max)."""
        basic = listing.get('basic_info', {})
        edition = listing.get('edition_details', {})

        parts = [basic.get('title', 'Book')]

        creator = basic.get('author') or basic.get('editor')
        if creator:
            if isinstance(creator, list):
                creator = creator[0]
            parts.append(f"by {creator.split(',')[0]}")

        if edition.get('is_signed'):
            parts.append('SIGNED')
        if edition.get('is_limited_edition'):
            parts.append('Limited Ed')

        title = ' '.join(parts)
        return title[:77] + '...' if len(title) > 80 else title

    def generate_description(self, listing: Dict) -> str:
        """Generate HTML description for eBay listing."""
        basic = listing.get('basic_info', {})
        edition = listing.get('edition_details', {})
        physical = listing.get('physical_details', {})
        notes = listing.get('notes', '')

        html = f"<h2>{basic.get('title', '')}</h2>"

        creator = basic.get('author') or basic.get('editor')
        if creator:
            label = 'Author' if basic.get('author') else 'Editor'
            html += f"<p><b>{label}:</b> {creator}</p>"

        if edition.get('edition_description'):
            html += f"<p><b>Edition:</b> {edition['edition_description']}</p>"

        if edition.get('is_signed'):
            signed_by = edition.get('signed_by', 'author')
            html += f"<p><b>Signed</b> by {signed_by}</p>"

        if physical.get('format'):
            html += f"<p><b>Format:</b> {physical['format']}</p>"

        if notes:
            html += f"<p>{notes}</p>"

        return html

    def listing_to_row(self, listing: Dict) -> Dict[str, Any]:
        """Convert a listing to eBay CSV row."""
        basic = listing.get('basic_info', {})
        pub = listing.get('publication_details', {})
        edition = listing.get('edition_details', {})
        physical = listing.get('physical_details', {})
        condition = listing.get('condition', {})
        images = listing.get('images', {})

        # Special attributes
        attrs = []
        if edition.get('is_signed'):
            attrs.append('Signed')
        if edition.get('is_limited_edition'):
            attrs.append('Limited Edition')
        if physical.get('has_slipcase'):
            attrs.append('Slipcase')
        if physical.get('has_dust_jacket'):
            attrs.append('Dust Jacket')

        # Image URLs (placeholder - would need actual URLs)
        image_files = images.get('files', [])
        pic_urls = '|'.join(image_files) if image_files else ''

        return {
            'Action': 'Add',
            'CustomLabel': listing.get('_dir', ''),
            'Title': self.generate_title(listing),
            'Category': '377',  # Antiquarian & Collectible
            'ConditionID': self.CONDITION_MAP.get(condition.get('overall_grade'), 4000),
            'C:Author': basic.get('author') or basic.get('editor', ''),
            'C:Publisher': pub.get('publisher', ''),
            'C:Publication Year': pub.get('publication_year', ''),
            'C:Format': physical.get('format', 'Hardcover'),
            'C:Language': 'English',
            'C:Signed': 'Yes' if edition.get('is_signed') else 'No',
            'C:Special Attributes': '|'.join(attrs),
            'PicURL': pic_urls,
            'Description': self.generate_description(listing),
            'Format': 'FixedPrice',
            'Duration': 'GTC',
            'StartPrice': '',  # User fills in
            'Quantity': '1',
            'Location': 'United States',
            'ShippingType': 'Flat',
            'ShippingService-1:Option': 'USPSMedia',
            'ShippingService-1:Cost': '',
            'ReturnsAcceptedOption': 'ReturnsAccepted',
            'ReturnPolicy': '14 Days'
        }

    def export_csv(self, output_path: Optional[Path] = None) -> Path:
        """Export all listings to eBay bulk upload CSV."""
        if output_path is None:
            output_path = self.listings_path.parent / 'exports' / f'ebay_upload_{datetime.now():%Y%m%d}.csv'

        output_path.parent.mkdir(parents=True, exist_ok=True)

        listings = self.load_listings()
        rows = [self.listing_to_row(l) for l in listings]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.EBAY_FIELDS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)

        return output_path


def export_to_ebay(listings_path: str, output_path: Optional[str] = None) -> str:
    """Quick function to export listings to eBay CSV."""
    exporter = EbayExporter(Path(listings_path))
    result = exporter.export_csv(Path(output_path) if output_path else None)
    return str(result)


if __name__ == '__main__':
    import sys
    listings_dir = sys.argv[1] if len(sys.argv) > 1 else './listings'
    output = export_to_ebay(listings_dir)
    print(f"Exported to: {output}")
