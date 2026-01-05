"""Export page - Generate eBay CSV and deploy.

Provides CSV generation with format selection, preview,
and one-click sync/deploy workflow.
"""

import streamlit as st
from pathlib import Path
import json
import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.gui.state import (
    get_selected_listings,
    clear_listing_selection,
    record_action
)
from src.core.title_generator import TitleGenerator
from src.utils.image_urls import ImageURLBuilder


def render():
    """Render the export page."""
    st.header("📦 Export to eBay")

    # Load listings
    project_root = Path(__file__).parent.parent.parent.parent
    listings_path = project_root / "listings"
    docs_path = project_root / "docs" / "listings"

    listings = load_listings(listings_path)

    if not listings:
        st.info("No listings to export. Create listings in the **Upload** tab first.")
        return

    # Selection
    selected = get_selected_listings()
    if selected:
        st.success(f"**{len(selected)}** listings selected for export")
        export_listings = [l for l in listings if l['_dir'] in selected]
    else:
        st.info(f"No specific selection. Will export all **{len(listings)}** listings.")
        export_listings = listings

    st.divider()

    # Export options
    st.subheader("Export Options")

    col1, col2 = st.columns(2)

    with col1:
        export_format = st.selectbox(
            "Format",
            ["Standard (23 fields)", "Extended (45+ fields)"],
            index=0,
            help="Standard format is recommended for most cases"
        )

    with col2:
        action_type = st.selectbox(
            "eBay Action",
            ["Add", "Draft"],
            index=0,
            help="'Add' creates live listings, 'Draft' saves as drafts"
        )

    st.divider()

    # Sync status
    st.subheader("Sync Status")

    synced_count = 0
    unsynced = []

    for listing in export_listings:
        dir_name = listing['_dir']
        docs_dir = docs_path / dir_name
        if docs_dir.exists():
            synced_count += 1
        else:
            unsynced.append(dir_name)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Synced to GitHub Pages", synced_count)
    with col2:
        st.metric("Not synced", len(unsynced))

    if unsynced:
        with st.expander(f"⚠️ {len(unsynced)} listings not synced"):
            for name in unsynced:
                st.text(f"  • {name}")
            st.warning("Run `make sync-images` to sync before exporting.")

    st.divider()

    # Preview
    st.subheader("Export Preview")

    # Generate preview data
    url_builder = ImageURLBuilder()
    preview_rows = []

    for listing in export_listings[:5]:  # Preview first 5
        row = generate_ebay_row(listing, url_builder, action_type)
        preview_rows.append(row)

    if preview_rows:
        # Show as table
        display_preview_table(preview_rows)

        if len(export_listings) > 5:
            st.caption(f"... and {len(export_listings) - 5} more listings")

    st.divider()

    # Export actions
    st.subheader("Export")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📋 Generate CSV", type="primary", use_container_width=True):
            csv_content = generate_csv(export_listings, url_builder, action_type)
            if csv_content:
                # Save to exports/
                exports_path = project_root / "exports"
                exports_path.mkdir(exist_ok=True)
                filename = f"ebay_upload_{datetime.now():%Y%m%d_%H%M%S}.csv"
                filepath = exports_path / filename

                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    f.write(csv_content)

                st.success(f"✓ Exported to `exports/{filename}`")
                record_action(f"exported:{filename}")

                # Also provide download
                st.download_button(
                    "⬇️ Download CSV",
                    csv_content,
                    file_name=filename,
                    mime="text/csv"
                )

    with col2:
        if st.button("🔄 Sync Images", use_container_width=True):
            st.info("Running `make sync-images`...")
            import subprocess
            result = subprocess.run(
                ["make", "sync-images"],
                cwd=str(project_root),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                st.success("✓ Images synced to docs/")
            else:
                st.error(f"Sync failed: {result.stderr}")

    with col3:
        if st.button("🚀 Deploy to GitHub", use_container_width=True):
            st.warning("This will commit and push to GitHub Pages.")
            if st.button("Confirm Deploy", key="confirm_deploy"):
                import subprocess
                result = subprocess.run(
                    ["make", "deploy"],
                    cwd=str(project_root),
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    st.success("✓ Deployed to GitHub Pages!")
                    st.info("Site will update in 1-2 minutes.")
                else:
                    st.error(f"Deploy failed: {result.stderr}")

    st.divider()

    # Quick workflow
    st.subheader("Quick Workflow")
    st.markdown("""
    1. **Sync Images** - Copy optimized images to docs/
    2. **Generate CSV** - Create eBay bulk upload file
    3. **Deploy** - Push to GitHub Pages (makes images live)
    4. **Upload to eBay** - Import CSV in Seller Hub
    """)

    if st.button("🔥 Run Complete Workflow", type="secondary", use_container_width=True):
        with st.spinner("Running complete workflow..."):
            import subprocess

            # Step 1: Sync
            st.info("Step 1: Syncing images...")
            result = subprocess.run(
                ["make", "sync-images"],
                cwd=str(project_root),
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                st.error(f"Sync failed: {result.stderr}")
                return

            # Step 2: Generate CSV
            st.info("Step 2: Generating CSV...")
            csv_content = generate_csv(export_listings, url_builder, action_type)
            exports_path = project_root / "exports"
            exports_path.mkdir(exist_ok=True)
            filename = f"ebay_upload_{datetime.now():%Y%m%d_%H%M%S}.csv"
            filepath = exports_path / filename
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)

            # Step 3: Deploy
            st.info("Step 3: Deploying to GitHub Pages...")
            result = subprocess.run(
                ["make", "deploy"],
                cwd=str(project_root),
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                st.success("✓ Complete workflow finished!")
                st.balloons()
                st.download_button(
                    "⬇️ Download CSV",
                    csv_content,
                    file_name=filename,
                    mime="text/csv"
                )
            else:
                st.warning(f"Deploy had issues: {result.stderr}")
                st.info("CSV was still generated successfully.")


def load_listings(listings_path: Path) -> List[Dict]:
    """Load all listings from disk."""
    listings = []

    if not listings_path.exists():
        return listings

    for item_dir in listings_path.iterdir():
        if item_dir.is_dir():
            metadata_path = item_dir / "metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        data = json.load(f)
                        data['_dir'] = item_dir.name
                        listings.append(data)
                except Exception:
                    pass

    return listings


def generate_ebay_row(listing: Dict, url_builder: ImageURLBuilder, action: str) -> Dict:
    """Generate a single eBay CSV row."""
    basic = listing.get('basic_info', {})
    pub = listing.get('publication_details', {})
    edition = listing.get('edition_details', {})
    physical = listing.get('physical_details', {})
    condition = listing.get('condition', {})
    images = listing.get('images', {})

    # Generate title and description
    title = TitleGenerator.generate_title(listing)
    description = TitleGenerator.generate_description(listing, format='html')

    # Build image URLs
    pic_urls = url_builder.build_urls(listing.get('_dir', ''), images)

    # Special attributes
    attrs = TitleGenerator.get_special_attributes(listing)

    # Condition mapping
    condition_map = {
        'NEW': 1000,
        'LIKE_NEW': 2750,
        'VERY_GOOD': 4000,
        'GOOD': 5000,
        'ACCEPTABLE': 6000
    }

    author = basic.get('author') or basic.get('editor', '')
    if isinstance(author, list):
        author = ', '.join(author)

    return {
        'Action': action,
        'CustomLabel': listing.get('_dir', ''),
        'Title': title,
        'Category': '377',
        'ConditionID': condition_map.get(condition.get('overall_grade', 'VERY_GOOD'), 4000),
        'C:Author': author,
        'C:Publisher': pub.get('publisher', ''),
        'C:Publication Year': pub.get('publication_year', ''),
        'C:Format': physical.get('format', 'Hardcover'),
        'C:Language': 'English',
        'C:Signed': 'Yes' if edition.get('is_signed') else 'No',
        'C:Special Attributes': '|'.join(attrs),
        'PicURL': pic_urls,
        'Description': description,
        'Format': 'FixedPrice',
        'Duration': 'GTC',
        'StartPrice': '',
        'Quantity': '1',
        'Location': 'United States',
        'ShippingType': 'Flat',
        'ShippingService-1:Option': 'USPSMedia',
        'ShippingService-1:Cost': '',
        'ReturnsAcceptedOption': 'ReturnsAccepted',
        'ReturnPolicy': '14 Days'
    }


def display_preview_table(rows: List[Dict]):
    """Display preview as a formatted table."""
    # Show key fields only
    display_fields = ['Title', 'C:Author', 'C:Signed', 'ConditionID']

    st.markdown("| Title | Author | Signed | Condition |")
    st.markdown("|-------|--------|--------|-----------|")

    for row in rows:
        title = row['Title'][:40] + '...' if len(row['Title']) > 40 else row['Title']
        author = row['C:Author'][:20] if row['C:Author'] else '-'
        signed = row['C:Signed']
        condition = str(row['ConditionID'])

        st.markdown(f"| {title} | {author} | {signed} | {condition} |")


def generate_csv(listings: List[Dict], url_builder: ImageURLBuilder, action: str) -> str:
    """Generate complete CSV content."""
    fields = [
        'Action', 'CustomLabel', 'Title', 'Category', 'ConditionID',
        'C:Author', 'C:Publisher', 'C:Publication Year', 'C:Format',
        'C:Language', 'C:Signed', 'C:Special Attributes',
        'PicURL', 'Description', 'Format', 'Duration', 'StartPrice',
        'Quantity', 'Location', 'ShippingType', 'ShippingService-1:Option',
        'ShippingService-1:Cost', 'ReturnsAcceptedOption', 'ReturnPolicy'
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()

    for listing in listings:
        row = generate_ebay_row(listing, url_builder, action)
        writer.writerow(row)

    return output.getvalue()
