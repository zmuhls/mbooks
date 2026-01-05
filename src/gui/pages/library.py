"""Library page - Browse and manage all listings.

Provides grid/list view of all book listings with filtering,
search, and quick edit capabilities.
"""

import streamlit as st
from pathlib import Path
import json
from typing import List, Dict, Any, Optional

from src.gui.state import (
    get_selected_listings,
    toggle_listing_selection,
    select_all_listings,
    clear_listing_selection,
    record_action,
    set_workflow_step
)
from src.core.title_generator import TitleGenerator


def render():
    """Render the library page."""
    st.header("📖 Library")

    # Load all listings
    project_root = Path(__file__).parent.parent.parent.parent
    listings_path = project_root / "listings"

    listings = load_all_listings(listings_path)

    if not listings:
        st.info("No listings found. Create your first listing in the **Upload** tab.")
        return

    # Filters and search
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        search = st.text_input(
            "🔍 Search",
            value=st.session_state.get('library_search', ''),
            placeholder="Search by title or author..."
        )
        st.session_state.library_search = search

    with col2:
        filter_signed = st.selectbox(
            "Signed",
            ["All", "Signed", "Not Signed"],
            index=0
        )

    with col3:
        filter_limited = st.selectbox(
            "Limited",
            ["All", "Limited", "Regular"],
            index=0
        )

    with col4:
        view_mode = st.radio(
            "View",
            ["Grid", "List"],
            horizontal=True,
            index=0 if st.session_state.get('library_view', 'grid') == 'grid' else 1
        )
        st.session_state.library_view = view_mode.lower()

    # Apply filters
    filtered = filter_listings(
        listings,
        search=search,
        signed=filter_signed,
        limited=filter_limited
    )

    st.divider()

    # Stats bar
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", len(listings))
    with col2:
        signed_count = len([l for l in listings if l.get('is_signed')])
        st.metric("Signed", signed_count)
    with col3:
        limited_count = len([l for l in listings if l.get('is_limited_edition')])
        st.metric("Limited Ed", limited_count)
    with col4:
        selected_count = len(get_selected_listings())
        st.metric("Selected", selected_count)

    st.divider()

    # Selection controls
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("Select All", use_container_width=True):
            select_all_listings([l['_dir'] for l in filtered])
            st.rerun()
    with col2:
        if st.button("Clear Selection", use_container_width=True):
            clear_listing_selection()
            st.rerun()

    # Display listings
    if view_mode.lower() == 'grid':
        render_grid_view(filtered, listings_path)
    else:
        render_list_view(filtered, listings_path)

    st.divider()

    # Bulk actions
    selected = get_selected_listings()
    if selected:
        st.subheader(f"Actions for {len(selected)} selected")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📦 Export Selected", type="primary", use_container_width=True):
                st.session_state.export_selection = selected
                set_workflow_step(4)
                st.info("Switch to **Export** tab to generate CSV.")

        with col2:
            if st.button("🔄 Sync to GitHub", use_container_width=True):
                st.info("Run `make sync-images` to sync selected listings.")


def load_all_listings(listings_path: Path) -> List[Dict]:
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
                        data['_path'] = str(item_dir)

                        # Flatten for easier access
                        basic = data.get('basic_info', {})
                        edition = data.get('edition_details', {})

                        data['title'] = basic.get('title', item_dir.name)
                        data['author'] = basic.get('author') or basic.get('editor', '')
                        data['is_signed'] = edition.get('is_signed', False)
                        data['is_limited_edition'] = edition.get('is_limited_edition', False)

                        # Count images
                        images = data.get('images', {})
                        data['image_count'] = len(images.get('files', []))
                        data['primary_image'] = images.get('primary_image')

                        listings.append(data)
                except Exception as e:
                    st.warning(f"Error loading {item_dir.name}: {e}")

    # Sort by last updated
    listings.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
    return listings


def filter_listings(
    listings: List[Dict],
    search: str = '',
    signed: str = 'All',
    limited: str = 'All'
) -> List[Dict]:
    """Filter listings by criteria."""
    result = listings

    # Search filter
    if search:
        search_lower = search.lower()
        result = [
            l for l in result
            if search_lower in l.get('title', '').lower()
            or search_lower in str(l.get('author', '')).lower()
        ]

    # Signed filter
    if signed == 'Signed':
        result = [l for l in result if l.get('is_signed')]
    elif signed == 'Not Signed':
        result = [l for l in result if not l.get('is_signed')]

    # Limited filter
    if limited == 'Limited':
        result = [l for l in result if l.get('is_limited_edition')]
    elif limited == 'Regular':
        result = [l for l in result if not l.get('is_limited_edition')]

    return result


def render_grid_view(listings: List[Dict], listings_path: Path):
    """Render listings in grid view."""
    cols_per_row = 3
    selected = get_selected_listings()

    for i in range(0, len(listings), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < len(listings):
                listing = listings[i + j]
                with col:
                    render_listing_card(listing, listings_path, selected)


def render_listing_card(listing: Dict, listings_path: Path, selected: List[str]):
    """Render a single listing card."""
    dir_name = listing['_dir']
    is_selected = dir_name in selected

    # Card container with border
    border_color = "#1e3a5f" if is_selected else "#ddd"

    with st.container():
        # Image
        primary = listing.get('primary_image')
        if primary:
            img_path = listings_path / dir_name / primary
            if img_path.exists():
                st.image(str(img_path), use_container_width=True)
            else:
                st.markdown("📷 No image")
        else:
            st.markdown("📷 No image")

        # Title
        st.markdown(f"**{listing.get('title', 'Untitled')[:40]}**")

        # Author
        author = listing.get('author', '')
        if isinstance(author, list):
            author = ', '.join(author)
        if author:
            st.caption(f"by {author[:30]}")

        # Tags
        tags = []
        if listing.get('is_signed'):
            tags.append("✓ Signed")
        if listing.get('is_limited_edition'):
            tags.append("📚 Limited")
        if tags:
            st.caption(' | '.join(tags))

        # Selection checkbox
        if st.checkbox(
            "Select",
            value=is_selected,
            key=f"select_{dir_name}"
        ):
            if not is_selected:
                toggle_listing_selection(dir_name)
        elif is_selected:
            toggle_listing_selection(dir_name)


def render_list_view(listings: List[Dict], listings_path: Path):
    """Render listings in list/table view."""
    selected = get_selected_listings()

    for listing in listings:
        dir_name = listing['_dir']
        is_selected = dir_name in selected

        col_check, col_img, col_info, col_actions = st.columns([0.5, 1, 4, 1])

        with col_check:
            if st.checkbox(
                "",
                value=is_selected,
                key=f"list_select_{dir_name}",
                label_visibility="collapsed"
            ):
                if not is_selected:
                    toggle_listing_selection(dir_name)
            elif is_selected:
                toggle_listing_selection(dir_name)

        with col_img:
            primary = listing.get('primary_image')
            if primary:
                img_path = listings_path / dir_name / primary
                if img_path.exists():
                    st.image(str(img_path), width=80)

        with col_info:
            # Title and author
            title = listing.get('title', 'Untitled')
            author = listing.get('author', '')
            if isinstance(author, list):
                author = ', '.join(author)

            st.markdown(f"**{title}**")
            if author:
                st.caption(f"by {author}")

            # Tags inline
            tags = []
            if listing.get('is_signed'):
                tags.append("Signed")
            if listing.get('is_limited_edition'):
                tags.append("Limited")
            if tags:
                st.caption(' | '.join(tags))

        with col_actions:
            if st.button("Edit", key=f"edit_{dir_name}"):
                # Load this listing for editing
                st.session_state.current_listing = dir_name
                set_workflow_step(2)
                st.info(f"Switch to **Edit** tab to modify {dir_name}")

        st.divider()
