"""Extract page - AI-powered metadata extraction.

Uses OpenRouter/Gemini vision API to extract book metadata from uploaded images.
Shows extraction progress, results preview, and allows proceeding to edit.
"""

import streamlit as st
from pathlib import Path
import base64
import json
import os
from typing import List, Dict, Any, Optional
from PIL import Image
import io

from src.gui.state import (
    get_image_groups,
    get_extracted_metadata,
    set_extracted_metadata,
    set_workflow_step,
    record_action
)


def render():
    """Render the extract page."""
    st.header("🔍 Extract Metadata")

    groups = get_image_groups()

    if not groups:
        st.warning("No images uploaded. Please go to the **Upload** tab first.")
        return

    # Show groups ready for extraction
    st.markdown(f"**{len(groups)} book group(s)** ready for extraction")

    for group_name, group in groups.items():
        with st.expander(f"📚 {group_name} ({group.image_count} images)", expanded=True):
            st.text(f"Images: {', '.join(group.images[:3])}{'...' if len(group.images) > 3 else ''}")
            st.text(f"Primary: {group.primary_image}")

    st.divider()

    # Extraction controls
    st.subheader("Extraction Settings")

    col1, col2 = st.columns(2)
    with col1:
        max_images = st.slider(
            "Max images to analyze",
            min_value=1,
            max_value=5,
            value=3,
            help="More images = better accuracy but higher API cost"
        )

    with col2:
        include_enrichment = st.checkbox(
            "Enrich with publication data",
            value=True,
            help="Look up additional publication details (publisher, year, genre)"
        )

    st.divider()

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        st.error("⚠️ OPENROUTER_API_KEY not set. Please set the environment variable.")
        st.code("export OPENROUTER_API_KEY='your-key-here'")
        return

    # Extract button
    if st.button("🤖 Extract Metadata", type="primary", use_container_width=True):
        extract_metadata_from_groups(groups, max_images, include_enrichment)

    # Show extracted metadata if available
    extracted = get_extracted_metadata()
    if extracted:
        st.divider()
        st.subheader("✓ Extracted Metadata")

        # Display in a nice format
        display_extracted_metadata(extracted)

        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Re-extract", use_container_width=True):
                st.session_state.extracted_metadata = None
                st.rerun()

        with col2:
            if st.button("➡️ Continue to Search", type="primary", use_container_width=True):
                record_action("extraction_complete")
                set_workflow_step(2)
                st.balloons()
                st.success("✅ Extraction complete! Click the **Search** tab above to enrich metadata.")

    # Show extraction status
    if st.session_state.get('extraction_status') == 'error':
        st.error(f"Extraction failed: {st.session_state.get('extraction_error', 'Unknown error')}")


def extract_metadata_from_groups(groups: Dict, max_images: int, enrich: bool):
    """Run extraction on image groups."""
    st.session_state.extraction_status = 'extracting'

    try:
        # For now, extract from first group
        # TODO: Handle multiple groups
        group_name = list(groups.keys())[0]
        group = groups[group_name]

        # Get image data from uploaded files
        uploaded_files = st.session_state.get('uploaded_files', [])
        if not uploaded_files:
            st.error("No uploaded files found in session.")
            return

        # Find images for this group
        group_images = []
        for img_name in group.images[:max_images]:
            for f in uploaded_files:
                if f.name == img_name:
                    f.seek(0)
                    img_data = f.read()
                    group_images.append({
                        'name': img_name,
                        'data': base64.b64encode(img_data).decode('utf-8'),
                        'type': get_image_media_type(img_name)
                    })
                    f.seek(0)
                    break

        if not group_images:
            st.error("Could not find image data.")
            return

        with st.spinner(f"Extracting metadata from {len(group_images)} images..."):
            # Call extraction API
            result = call_extraction_api(group_images)

            if result:
                # Enrich if requested
                if enrich and result.get('title'):
                    with st.spinner("Enriching with publication data..."):
                        result = enrich_metadata(result)

                set_extracted_metadata(result)
                st.session_state.tokens_used = result.get('_tokens_used', 0)
                st.success("✓ Extraction complete!")
                st.rerun()
            else:
                st.error("Extraction returned no results.")
                st.session_state.extraction_status = 'error'

    except Exception as e:
        st.session_state.extraction_status = 'error'
        st.session_state.extraction_error = str(e)
        st.error(f"Extraction failed: {e}")


def call_extraction_api(images: List[Dict]) -> Optional[Dict]:
    """Call OpenRouter API for metadata extraction.

    Args:
        images: List of image dicts with 'data' (base64) and 'type' (mime)

    Returns:
        Extracted metadata dict or None
    """
    try:
        from openai import OpenAI

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

        # Build message with images
        content = [
            {"type": "text", "text": EXTRACTION_PROMPT}
        ]

        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{img['type']};base64,{img['data']}"
                }
            })

        response = client.chat.completions.create(
            model="google/gemini-3-flash-preview",
            messages=[{"role": "user", "content": content}],
            max_tokens=2000,
        )

        # Parse response
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0

        # Extract JSON from response
        metadata = parse_json_response(text)
        if metadata:
            metadata['_tokens_used'] = tokens
            metadata['_raw_response'] = text

        return metadata

    except ImportError:
        st.error("OpenAI package not installed. Run: pip install openai")
        return None
    except Exception as e:
        st.error(f"API call failed: {e}")
        return None


def enrich_metadata(metadata: Dict) -> Dict:
    """Enrich metadata with publication lookup."""
    # Simple enrichment - can be expanded
    # For now, just ensure required fields exist
    if 'publication_details' not in metadata:
        metadata['publication_details'] = {}

    return metadata


def parse_json_response(text: str) -> Optional[Dict]:
    """Parse JSON from API response, handling markdown code blocks."""
    # Try to find JSON in code blocks
    import re
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        text = json_match.group(1)

    # Try to parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
    return None


def display_extracted_metadata(metadata: Dict):
    """Display extracted metadata in a readable format."""
    # Basic info
    st.markdown("**Basic Information**")
    col1, col2 = st.columns(2)
    with col1:
        st.text(f"Title: {metadata.get('title', 'Unknown')}")
        st.text(f"Author: {metadata.get('author', 'Unknown')}")
    with col2:
        st.text(f"Publisher: {metadata.get('publisher', 'Unknown')}")
        st.text(f"Year: {metadata.get('publication_year', 'Unknown')}")

    # Edition details
    if metadata.get('is_signed') or metadata.get('is_limited_edition'):
        st.markdown("**Edition Details**")
        if metadata.get('is_signed'):
            st.success(f"✓ Signed by: {metadata.get('signed_by', 'author')}")
        if metadata.get('is_limited_edition'):
            st.info(f"Limited Edition: {metadata.get('limitation_statement', 'Yes')}")

    # Condition
    if metadata.get('condition_observations'):
        st.markdown("**Condition**")
        st.text(metadata.get('condition_observations'))

    # Token usage
    tokens = metadata.get('_tokens_used', 0)
    if tokens:
        st.caption(f"API tokens used: {tokens}")


def get_image_media_type(filename: str) -> str:
    """Get MIME type for image file."""
    suffix = Path(filename).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix, "image/jpeg")


# Extraction prompt
EXTRACTION_PROMPT = """Analyze these book images and extract all visible metadata.
Return ONLY a valid JSON object with these fields (use null for unknown values):

{
    "title": "Full book title as shown",
    "subtitle": "Subtitle if visible",
    "author": "Author name(s) - use array for multiple",
    "editor": "Editor name(s) for anthologies",
    "illustrator": "Illustrator if credited",
    "publisher": "Publisher name",
    "publication_year": 2024,
    "isbn": "ISBN if visible",
    "edition_description": "Edition statement (First Edition, Limited Edition, etc.)",
    "is_limited_edition": true/false,
    "limitation_statement": "e.g., 'Limited to 500 copies'",
    "copy_number": "Copy number or letter if visible",
    "is_signed": true/false,
    "signed_by": "Who signed (author name, 'author', etc.)",
    "signature_notes": "Location/type of signature",
    "binding_type": "Cloth, Leather, etc.",
    "binding_color": "Color of binding",
    "format": "Hardcover, Paperback, etc.",
    "has_dust_jacket": true/false,
    "has_slipcase": true/false,
    "gilt_details": "Gilt lettering/edges details",
    "condition_observations": "Overall condition notes from what's visible"
}

Be thorough but only include information you can actually see in the images.
Return ONLY the JSON object, no other text."""
