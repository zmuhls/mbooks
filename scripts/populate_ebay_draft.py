#!/usr/bin/env python3
"""Populate eBay draft listing template with book data."""

import json
import csv
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils.image_urls import ImageURLBuilder


def generate_title(listing):
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


def generate_description(listing):
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


def get_condition_id(listing):
    """Get eBay condition name."""
    condition_map = {
        'NEW': 'NEW',
        'LIKE_NEW': 'Like New',
        'VERY_GOOD': 'Very Good',
        'GOOD': 'Good',
        'ACCEPTABLE': 'Acceptable'
    }
    condition = listing.get('condition', {})
    grade = condition.get('overall_grade', 'VERY_GOOD')
    return condition_map.get(grade, 'Very Good')


def load_listings():
    """Load all metadata.json files from listings directory."""
    listings_path = Path('listings')
    listings = []

    for item_dir in listings_path.iterdir():
        if item_dir.is_dir():
            metadata_file = item_dir / 'metadata.json'
            if metadata_file.exists():
                with open(metadata_file) as f:
                    data = json.load(f)
                    data['_dir'] = item_dir.name
                    listings.append(data)

    return listings


def populate_template(output_file):
    """Populate eBay draft template with listings."""
    listings = load_listings()
    url_builder = ImageURLBuilder()

    # Write the file with proper headers
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        # Write INFO headers
        f.write('#INFO,Version=0.0.2,Template= eBay-draft-listings-template_US,,,,,,,,\n')
        f.write('#INFO Action and Category ID are required fields. 1) Set Action to Draft 2) Please find the category ID for your listings here: https://pages.ebay.com/sellerinformation/news/categorychanges.html,,,,,,,,,,\n')
        f.write('"#INFO After you\'ve successfully uploaded your draft from the Seller Hub Reports tab, complete your drafts to active listings here: https://www.ebay.com/sh/lst/drafts",,,,,,,,,,\n')
        f.write('#INFO,,,,,,,,,,\n')

        # Write column headers
        writer = csv.writer(f)
        headers = [
            'Action(SiteID=US|Country=US|Currency=USD|Version=1193|CC=UTF-8)',
            'Custom label (SKU)',
            'Category ID',
            'Title',
            'UPC',
            'Price',
            'Quantity',
            'Item photo URL',
            'Condition ID',
            'Description',
            'Format'
        ]
        writer.writerow(headers)

        # Write listings
        for listing in listings:
            images = listing.get('images', {})
            image_urls = url_builder.build_urls(listing['_dir'], images)

            row = [
                'Draft',  # Action
                listing['_dir'],  # Custom label (SKU)
                '377',  # Category ID - Antiquarian & Collectible
                generate_title(listing),  # Title
                '',  # UPC
                '',  # Price (user fills in)
                '1',  # Quantity
                image_urls,  # Item photo URL
                get_condition_id(listing),  # Condition ID
                generate_description(listing),  # Description
                'FixedPrice'  # Format
            ]
            writer.writerow(row)

    print(f'✅ Populated template with {len(listings)} listings')
    print(f'📄 Output: {output_file}')


if __name__ == '__main__':
    template_file = 'eBay-draft-listing-template-Dec-29-2025-11-32-11.csv'
    populate_template(template_file)
