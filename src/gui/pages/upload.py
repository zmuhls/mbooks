"""Upload page - Image upload and grouping interface.

Provides drag-drop file upload, image preview grid, automatic grouping
by filename pattern, and primary image selection.
"""

import streamlit as st
from pathlib import Path
import re
from typing import List, Dict, Optional
from PIL import Image, ImageOps
import io

from src.gui.state import (
    add_image_group,
    get_image_groups,
    remove_image_group,
    reset_upload_state,
    set_workflow_step,
    record_action
)


def render():
    """Render the upload page."""
    st.header("📤 Upload Book Images")

    st.markdown("""
    Upload images for a new book listing. You can upload multiple images at once.
    Images will be automatically grouped by filename pattern (e.g., IMG_5510, IMG_5511 → same book).
    """)

    # File uploader
    uploaded_files = st.file_uploader(
        "Drop book images here",
        type=['jpg', 'jpeg', 'png', 'webp'],
        accept_multiple_files=True,
        help="Upload JPEG, PNG, or WebP images"
    )

    if uploaded_files:
        # Store in session state
        st.session_state.uploaded_files = uploaded_files

        st.success(f"✓ {len(uploaded_files)} image(s) uploaded")

        # Show image preview grid
        st.subheader("Image Preview")

        # Create columns for grid display
        cols_per_row = 4
        rows = (len(uploaded_files) + cols_per_row - 1) // cols_per_row

        for row_idx in range(rows):
            cols = st.columns(cols_per_row)
            for col_idx in range(cols_per_row):
                img_idx = row_idx * cols_per_row + col_idx
                if img_idx < len(uploaded_files):
                    with cols[col_idx]:
                        file = uploaded_files[img_idx]
                        # Display thumbnail with EXIF orientation fix
                        image = Image.open(file)
                        image = ImageOps.exif_transpose(image)
                        st.image(image, caption=file.name, use_container_width=True)
                        # Reset file position for later use
                        file.seek(0)

        st.divider()

        # Automatic grouping
        st.subheader("Image Grouping")

        groups = auto_group_images([f.name for f in uploaded_files])

        if len(groups) == 1:
            group_name = list(groups.keys())[0]
            st.info(f"All images appear to be from the same book: **{group_name}**")
        elif len(groups) > 1:
            st.warning(f"Detected **{len(groups)} possible book groups** based on filenames. Please review.")

        # Display and edit groups
        for group_name, image_names in groups.items():
            with st.expander(f"📚 {group_name} ({len(image_names)} images)", expanded=True):
                # Show images in this group
                group_cols = st.columns(min(len(image_names), 4))
                for idx, img_name in enumerate(image_names[:4]):
                    with group_cols[idx]:
                        # Find the file object
                        for f in uploaded_files:
                            if f.name == img_name:
                                img = Image.open(f)
                                img = ImageOps.exif_transpose(img)
                                st.image(img, caption=img_name, use_container_width=True)
                                f.seek(0)
                                break

                if len(image_names) > 4:
                    st.caption(f"... and {len(image_names) - 4} more images")

                # Primary image selection
                primary = st.selectbox(
                    "Primary Image (shown first on eBay)",
                    image_names,
                    key=f"primary_{group_name}",
                    help="This image will be the main photo in the eBay listing"
                )

                # Store group
                add_image_group(group_name, image_names, primary)

        st.divider()

        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("🔄 Reset", use_container_width=True):
                reset_upload_state()
                st.rerun()

        with col2:
            if st.button("➡️ Continue to Extract", type="primary", use_container_width=True):
                if get_image_groups():
                    record_action("upload_complete")
                    set_workflow_step(1)
                    st.success("Ready to extract metadata!")
                    st.info("Switch to the **Extract** tab to continue.")
                else:
                    st.error("Please upload at least one image.")

    else:
        # Show placeholder when no files uploaded
        st.markdown("""
        <div style="border: 2px dashed #ccc; border-radius: 10px; padding: 60px; text-align: center; background-color: #fafafa; color: #333;">
            <h3 style="color: #333;">📷 Drop images here</h3>
            <p style="color: #555;">or click to browse</p>
            <p style="color: #888; font-size: 0.9em;">Supported formats: JPEG, PNG, WebP</p>
        </div>
        """, unsafe_allow_html=True)

        # Alternative: process from incoming_images directory
        st.divider()
        st.subheader("Or process from incoming_images/")

        incoming_path = Path(__file__).parent.parent.parent.parent / "incoming_images"
        if incoming_path.exists():
            image_files = list(incoming_path.glob("*.jpg")) + list(incoming_path.glob("*.jpeg")) + list(incoming_path.glob("*.png"))
            if image_files:
                st.info(f"Found {len(image_files)} images in `incoming_images/`")
                if st.button("📂 Load from incoming_images/"):
                    st.session_state.incoming_mode = True
                    st.session_state.incoming_files = [str(f) for f in image_files]
                    record_action("load_incoming")
                    st.success(f"Loaded {len(image_files)} images from incoming_images/")
                    st.rerun()
            else:
                st.caption("No images found in incoming_images/")
        else:
            st.caption("incoming_images/ directory not found")


def auto_group_images(filenames: List[str]) -> Dict[str, List[str]]:
    """Automatically group images by filename pattern.

    Groups images that appear to be from the same photo session:
    - Sequential numbers (IMG_5510, IMG_5511, IMG_5512)
    - Same prefix with different suffixes

    Args:
        filenames: List of image filenames

    Returns:
        Dict mapping group names to lists of filenames
    """
    if not filenames:
        return {}

    # Sort filenames
    sorted_files = sorted(filenames)

    # Extract base patterns
    groups: Dict[str, List[str]] = {}

    for filename in sorted_files:
        # Try to find a pattern like IMG_5510.jpg -> IMG_551
        # This groups IMG_5510-5519 together

        name = Path(filename).stem  # Remove extension

        # Pattern: word_numbers -> group by prefix and tens digit
        match = re.match(r'^(.+?)(\d+)$', name)
        if match:
            prefix = match.group(1)
            number = match.group(2)

            # Group by prefix + first N-1 digits (groups of 10)
            if len(number) >= 2:
                group_key = f"{prefix}{number[:-1]}"
            else:
                group_key = prefix
        else:
            # No number pattern, use the whole name
            group_key = name

        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(filename)

    # If we have many small groups, might want to merge them
    # For now, if everything is in separate groups, combine into one
    if len(groups) == len(filenames):
        # Each file is its own group - likely same book
        return {"new_book": sorted_files}

    return groups


def get_image_bytes(file) -> bytes:
    """Get image bytes from uploaded file."""
    file.seek(0)
    return file.read()
