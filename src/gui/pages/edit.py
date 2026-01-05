"""Edit page - Metadata editing form with title preview.

Provides a comprehensive form for editing all metadata fields,
live eBay title preview, and image optimization controls.
"""

import streamlit as st
from pathlib import Path
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
from PIL import Image, ImageOps
import io

from src.gui.state import (
    get_extracted_metadata,
    get_form_data,
    set_form_data,
    update_form_data,
    mark_changes_saved,
    has_unsaved_changes,
    record_action,
    set_workflow_step
)
from src.core.title_generator import TitleGenerator


def render():
    """Render the edit page."""
    st.header("✏️ Edit Metadata")

    # Get data to edit
    extracted = get_extracted_metadata()
    form_data = get_form_data()

    # Initialize form data from extracted if empty
    if not form_data and extracted:
        try:
            form_data = convert_extracted_to_form(extracted)
            set_form_data(form_data)
        except Exception as e:
            st.error(f"Error converting extracted data: {e}")
            form_data = {}

    # If still no form data, check if we have image groups to start from scratch
    if not form_data:
        from src.gui.state import get_image_groups
        groups = get_image_groups()

        if groups:
            st.info("No extracted metadata found. You can fill in the form manually or go back to Extract.")
            # Initialize with empty form data
            form_data = {
                'title': '',
                'subtitle': '',
                'author': '',
                'editor': '',
                'illustrator': '',
                'is_signed': False,
                'is_limited_edition': False,
                'format': 'Hardcover',
                'overall_grade': 'VERY_GOOD',
            }
            set_form_data(form_data)
        else:
            st.warning("No images uploaded yet. Please go to the **Upload** tab first.")
            if st.button("⬅️ Go to Upload"):
                set_workflow_step(0)
                st.info("Switch to the **Upload** tab to add images.")
            return

    # Layout: form on left, preview on right
    col_form, col_preview = st.columns([2, 1])

    with col_form:
        render_metadata_form(form_data)

    with col_preview:
        render_preview_panel(form_data)

    st.divider()

    # Action buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔄 Reset to Extracted", use_container_width=True):
            if extracted:
                form_data = convert_extracted_to_form(extracted)
                set_form_data(form_data)
                st.rerun()

    with col2:
        slug = generate_slug(form_data.get('title', 'new_book'))
        if st.button("💾 Save Listing", type="primary", use_container_width=True):
            save_listing(form_data, slug)

    with col3:
        if st.button("📖 View in Library", use_container_width=True):
            set_workflow_step(4)
            st.info("Switch to the **Library** tab to browse listings.")

    with col4:
        if st.button("📦 Go to Export", use_container_width=True):
            set_workflow_step(5)
            st.info("Switch to the **Export** tab to generate eBay CSV.")


def render_metadata_form(form_data: Dict):
    """Render the full metadata editing form."""

    # === BASIC INFO ===
    st.subheader("📖 Basic Information")

    form_data['title'] = st.text_input(
        "Title *",
        value=form_data.get('title', ''),
        help="Full book title"
    )

    form_data['subtitle'] = st.text_input(
        "Subtitle",
        value=form_data.get('subtitle', ''),
        help="Subtitle if applicable"
    )

    # Author/Editor toggle
    creator_type = st.radio(
        "Creator Type",
        ["Author", "Editor"],
        horizontal=True,
        index=0 if form_data.get('author') else 1
    )

    if creator_type == "Author":
        form_data['author'] = st.text_input(
            "Author",
            value=form_data.get('author', ''),
            help="Author name(s), comma-separated for multiple"
        )
        form_data['editor'] = None
    else:
        form_data['editor'] = st.text_input(
            "Editor",
            value=form_data.get('editor', ''),
            help="Editor name(s) for anthologies"
        )
        form_data['author'] = None

    form_data['illustrator'] = st.text_input(
        "Illustrator",
        value=form_data.get('illustrator', ''),
        help="Illustrator if credited"
    )

    st.divider()

    # === EDITION DETAILS ===
    st.subheader("✨ Edition Details")

    col1, col2 = st.columns(2)

    with col1:
        form_data['is_signed'] = st.checkbox(
            "Signed",
            value=form_data.get('is_signed', False)
        )

        if form_data['is_signed']:
            form_data['signed_by'] = st.text_input(
                "Signed By",
                value=form_data.get('signed_by', ''),
                help="Who signed the book"
            )
            form_data['signature_notes'] = st.text_area(
                "Signature Notes",
                value=form_data.get('signature_notes', ''),
                height=60,
                help="Location, inscription details, etc."
            )

    with col2:
        form_data['is_limited_edition'] = st.checkbox(
            "Limited Edition",
            value=form_data.get('is_limited_edition', False)
        )

        if form_data['is_limited_edition']:
            form_data['edition_size'] = st.number_input(
                "Edition Size",
                min_value=1,
                value=form_data.get('edition_size', 500),
                help="Total number of copies"
            )
            form_data['copy_number'] = st.text_input(
                "Copy Number/Letter",
                value=form_data.get('copy_number', ''),
                help="e.g., '42' or 'A'"
            )

    form_data['edition_description'] = st.text_input(
        "Edition Description",
        value=form_data.get('edition_description', ''),
        help="e.g., 'First Edition, First Printing'"
    )

    st.divider()

    # === PUBLICATION DETAILS ===
    st.subheader("📚 Publication Details")

    col1, col2 = st.columns(2)

    with col1:
        form_data['publisher'] = st.text_input(
            "Publisher",
            value=form_data.get('publisher', '')
        )
        form_data['publication_year'] = st.number_input(
            "Publication Year",
            min_value=1800,
            max_value=datetime.now().year + 1,
            value=form_data.get('publication_year') or datetime.now().year,
            help="Year this edition was published"
        )

    with col2:
        form_data['isbn'] = st.text_input(
            "ISBN",
            value=form_data.get('isbn', ''),
            help="10 or 13 digit ISBN"
        )
        form_data['page_count'] = st.number_input(
            "Page Count",
            min_value=1,
            value=form_data.get('page_count') or 200,
            help="Number of pages"
        )

    st.divider()

    # === PHYSICAL DETAILS ===
    st.subheader("📏 Physical Details")

    col1, col2 = st.columns(2)

    with col1:
        form_data['format'] = st.selectbox(
            "Format",
            ["Hardcover", "Paperback", "Trade Paperback", "Leather Bound"],
            index=["Hardcover", "Paperback", "Trade Paperback", "Leather Bound"].index(
                form_data.get('format', 'Hardcover')
            ) if form_data.get('format') in ["Hardcover", "Paperback", "Trade Paperback", "Leather Bound"] else 0
        )

        form_data['binding_type'] = st.text_input(
            "Binding Type",
            value=form_data.get('binding_type', ''),
            help="e.g., Cloth, Leather, Boards"
        )

        form_data['binding_color'] = st.text_input(
            "Binding Color",
            value=form_data.get('binding_color', ''),
            help="Color of the binding"
        )

    with col2:
        form_data['has_dust_jacket'] = st.checkbox(
            "Has Dust Jacket",
            value=form_data.get('has_dust_jacket', False)
        )

        form_data['has_slipcase'] = st.checkbox(
            "Has Slipcase",
            value=form_data.get('has_slipcase', False)
        )

        form_data['gilt_details'] = st.text_input(
            "Gilt Details",
            value=form_data.get('gilt_details', ''),
            help="Gilt lettering, edges, etc."
        )

    st.divider()

    # === CONDITION ===
    st.subheader("⭐ Condition")

    form_data['overall_grade'] = st.selectbox(
        "Overall Grade",
        ["NEW", "LIKE_NEW", "VERY_GOOD", "GOOD", "ACCEPTABLE"],
        index=["NEW", "LIKE_NEW", "VERY_GOOD", "GOOD", "ACCEPTABLE"].index(
            form_data.get('overall_grade', 'VERY_GOOD')
        ) if form_data.get('overall_grade') in ["NEW", "LIKE_NEW", "VERY_GOOD", "GOOD", "ACCEPTABLE"] else 2
    )

    form_data['condition_notes'] = st.text_area(
        "Condition Notes",
        value=form_data.get('condition_notes', ''),
        height=80,
        help="Detailed condition description"
    )

    # Defects as comma-separated
    defects_str = ', '.join(form_data.get('defects', []))
    defects_input = st.text_input(
        "Defects (comma-separated)",
        value=defects_str,
        help="e.g., 'minor shelf wear, small tear on dust jacket'"
    )
    form_data['defects'] = [d.strip() for d in defects_input.split(',') if d.strip()]

    st.divider()

    # === NOTES ===
    st.subheader("📝 Notes")

    form_data['notes'] = st.text_area(
        "Listing Notes",
        value=form_data.get('notes', ''),
        height=100,
        help="Additional notes for the eBay listing"
    )

    # Update session state
    set_form_data(form_data)


def render_preview_panel(form_data: Dict):
    """Render the preview panel with title and description."""

    st.subheader("📋 Preview")

    # Convert form data to metadata format for title generator
    metadata = convert_form_to_metadata(form_data)

    # Generate title
    title = TitleGenerator.generate_title(metadata)
    title_status = TitleGenerator.get_title_length_status(title)

    # Title preview with color coding
    st.markdown("**eBay Title:**")

    status_class = {
        'good': 'title-good',
        'warning': 'title-warning',
        'danger': 'title-danger'
    }.get(title_status['status'], '')

    st.markdown(f"""
    <div class="title-preview {status_class}">
        {title}
    </div>
    """, unsafe_allow_html=True)

    # Character count
    color = {'good': '🟢', 'warning': '🟡', 'danger': '🔴'}.get(title_status['status'], '⚪')
    st.caption(f"{color} {title_status['length']}/80 characters ({title_status['remaining']} remaining)")

    st.divider()

    # Quick stats
    st.markdown("**Listing Stats:**")
    cols = st.columns(2)

    with cols[0]:
        if form_data.get('is_signed'):
            st.success("✓ Signed")
        else:
            st.text("○ Not signed")

    with cols[1]:
        if form_data.get('is_limited_edition'):
            st.info("✓ Limited")
        else:
            st.text("○ Regular")

    # Show special attributes
    attrs = TitleGenerator.get_special_attributes(metadata)
    if attrs:
        st.markdown("**Special Attributes:**")
        st.text(', '.join(attrs))

    st.divider()

    # Slug preview
    slug = generate_slug(form_data.get('title', ''))
    st.markdown("**Directory Name:**")
    st.code(slug)

    # Image optimization settings
    st.divider()
    st.markdown("**Image Settings:**")

    bg_mode = st.session_state.get('background_mode', 'blur')
    st.text(f"Background: {bg_mode}")

    if bg_mode == 'blur':
        st.text(f"Blur radius: {st.session_state.get('blur_radius', 15)}px")


def convert_extracted_to_form(extracted: Dict) -> Dict:
    """Convert extracted metadata to form data format.

    Handles both flat API responses and nested metadata structures.
    """
    # Helper to safely get nested values
    def get_val(keys, default=''):
        """Get value from nested dict or flat dict."""
        if isinstance(keys, str):
            keys = [keys]

        # Try flat access first
        if len(keys) == 1 and keys[0] in extracted:
            val = extracted[keys[0]]
            return val if val is not None else default

        # Try nested access
        val = extracted
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key)
            else:
                return default
        return val if val is not None else default

    # Handle author field (can be string or list)
    author = get_val('author')
    if isinstance(author, list):
        author = ', '.join(author)

    editor = get_val('editor')
    if isinstance(editor, list):
        editor = ', '.join(editor)

    # Convert boolean strings to actual booleans
    def to_bool(val):
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ('true', 'yes', '1')
        return bool(val) if val else False

    return {
        'title': str(get_val('title', '')),
        'subtitle': str(get_val('subtitle', '')),
        'author': str(author) if author else '',
        'editor': str(editor) if editor else '',
        'illustrator': str(get_val('illustrator', '')),
        'is_signed': to_bool(get_val('is_signed', False)),
        'signed_by': str(get_val('signed_by', '')),
        'signature_notes': str(get_val('signature_notes', '')),
        'is_limited_edition': to_bool(get_val('is_limited_edition', False)),
        'edition_size': get_val('edition_size'),
        'copy_number': str(get_val('copy_number', '')),
        'edition_description': str(get_val('edition_description', '')),
        'publisher': str(get_val('publisher', '')),
        'publication_year': get_val('publication_year'),
        'isbn': str(get_val('isbn', '')),
        'page_count': get_val('page_count'),
        'format': str(get_val('format', 'Hardcover')),
        'binding_type': str(get_val('binding_type', '')),
        'binding_color': str(get_val('binding_color', '')),
        'has_dust_jacket': to_bool(get_val('has_dust_jacket', False)),
        'has_slipcase': to_bool(get_val('has_slipcase', False)),
        'gilt_details': str(get_val('gilt_details', '')),
        'overall_grade': str(get_val('overall_grade', 'VERY_GOOD')),
        'condition_notes': str(get_val('condition_observations', get_val('condition_notes', ''))),
        'defects': get_val('defects', []) or [],
        'notes': str(get_val('notes', '')),
    }


def convert_form_to_metadata(form_data: Dict) -> Dict:
    """Convert form data to nested metadata format."""
    return {
        'basic_info': {
            'title': form_data.get('title', ''),
            'subtitle': form_data.get('subtitle'),
            'author': form_data.get('author'),
            'editor': form_data.get('editor'),
            'illustrator': form_data.get('illustrator'),
        },
        'edition_details': {
            'is_signed': form_data.get('is_signed', False),
            'signed_by': form_data.get('signed_by'),
            'signature_notes': form_data.get('signature_notes'),
            'is_limited_edition': form_data.get('is_limited_edition', False),
            'edition_size': form_data.get('edition_size'),
            'copy_identifier': {
                'type': 'numbered',
                'value': form_data.get('copy_number')
            } if form_data.get('copy_number') else None,
            'edition_description': form_data.get('edition_description'),
        },
        'publication_details': {
            'publisher': form_data.get('publisher'),
            'publication_year': form_data.get('publication_year'),
            'isbn_13': form_data.get('isbn') if form_data.get('isbn') and len(form_data.get('isbn', '')) == 13 else None,
            'isbn_10': form_data.get('isbn') if form_data.get('isbn') and len(form_data.get('isbn', '')) == 10 else None,
            'page_count': form_data.get('page_count'),
        },
        'physical_details': {
            'format': form_data.get('format', 'Hardcover'),
            'binding_type': form_data.get('binding_type'),
            'binding_color': form_data.get('binding_color'),
            'has_dust_jacket': form_data.get('has_dust_jacket', False),
            'has_slipcase': form_data.get('has_slipcase', False),
            'gilt_details': form_data.get('gilt_details'),
        },
        'condition': {
            'overall_grade': form_data.get('overall_grade', 'VERY_GOOD'),
            'condition_notes': form_data.get('condition_notes'),
            'defects': form_data.get('defects', []),
        },
        'notes': form_data.get('notes'),
    }


def generate_slug(title: str) -> str:
    """Generate URL-safe slug from title."""
    if not title:
        return "new_book"

    # Lowercase and replace spaces/special chars
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')

    # Limit length
    if len(slug) > 50:
        slug = slug[:50].rsplit('_', 1)[0]

    return slug or "new_book"


def save_listing(form_data: Dict, slug: str):
    """Save the listing to disk."""
    try:
        # Get project paths
        project_root = Path(__file__).parent.parent.parent.parent
        listings_path = project_root / "listings" / slug

        # Create directory
        listings_path.mkdir(parents=True, exist_ok=True)

        # Build full metadata
        metadata = convert_form_to_metadata(form_data)

        # Add schema info
        metadata['schema_version'] = '1.0'
        metadata['last_updated'] = datetime.now().isoformat()

        # Add images info (from session state)
        from src.gui.state import get_image_groups
        groups = get_image_groups()
        if groups:
            group = list(groups.values())[0]
            metadata['images'] = {
                'files': group.images,
                'primary_image': group.primary_image,
                'image_notes': {}
            }

            # Copy images to listing directory (with EXIF orientation fix)
            uploaded_files = st.session_state.get('uploaded_files', [])
            for img_name in group.images:
                for f in uploaded_files:
                    if f.name == img_name:
                        f.seek(0)
                        # Apply EXIF orientation before saving
                        img = Image.open(f)
                        img = ImageOps.exif_transpose(img)
                        # Convert to RGB if necessary (handles RGBA, P modes)
                        if img.mode in ('RGBA', 'P'):
                            img = img.convert('RGB')
                        img_path = listings_path / img_name
                        img.save(img_path, 'JPEG', quality=95)
                        f.seek(0)
                        break

        # Save metadata.json
        metadata_path = listings_path / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        mark_changes_saved()
        record_action(f"saved_listing:{slug}")

        st.success(f"✓ Saved listing to `listings/{slug}/`")
        st.info("Run `make sync-images` to sync to GitHub Pages.")

    except Exception as e:
        st.error(f"Failed to save: {e}")
