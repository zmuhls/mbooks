"""Session state management for the Streamlit GUI.

Centralizes all session state initialization and provides helper functions
for managing state across pages.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ImageGroup:
    """Represents a group of images for a single book."""
    name: str
    images: List[str] = field(default_factory=list)
    primary_image: Optional[str] = None

    @property
    def image_count(self) -> int:
        return len(self.images)


def init_session_state():
    """Initialize all session state variables.

    Should be called once at app startup. Safe to call multiple times
    as it only sets defaults for missing keys.
    """
    defaults = {
        # Upload state
        'uploaded_files': [],
        'image_groups': {},  # Dict[group_name, ImageGroup]
        'current_group': None,

        # Extraction state
        'extraction_provider': 'openrouter',
        'extracted_metadata': None,
        'extraction_status': 'idle',  # idle, extracting, complete, error
        'extraction_error': None,
        'tokens_used': 0,

        # Edit state
        'current_listing': None,  # Directory name
        'form_data': {},
        'unsaved_changes': False,

        # Library state
        'library_filter_signed': None,
        'library_filter_limited': None,
        'library_search': '',
        'library_view': 'grid',  # grid or list
        'selected_listings': [],

        # Export state
        'export_format': 'standard',  # standard, extended, draft
        'export_preview': None,
        'last_export_path': None,

        # Settings
        'background_mode': 'blur',  # blur, white, none
        'blur_radius': 15,
        'brightness_boost': 1.15,
        'max_dimension': 1600,
        'jpeg_quality': 90,

        # Search state
        'search_status': 'idle',  # idle, searching, complete, error
        'search_queries': {},  # Generated queries {type: query_text}
        'search_results': {},  # Raw results from search provider
        'search_matches': {},  # Parsed field matches with confidence
        'search_accepted': {},  # User-accepted values
        'search_rejected': {},  # User-rejected values
        'search_pricing': None,  # Comparable pricing data
        'search_provider': 'perplexity',  # API provider
        'search_tokens_used': 0,  # Track API usage
        'search_error': None,  # Error message if any

        # Workflow tracking
        'workflow_step': 0,  # 0=upload, 1=extract, 2=search, 3=edit, 4=library, 5=export
        'last_action': None,
        'last_action_time': None,
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def reset_upload_state():
    """Reset upload-related state."""
    st.session_state.uploaded_files = []
    st.session_state.image_groups = {}
    st.session_state.current_group = None


def reset_extraction_state():
    """Reset extraction-related state."""
    st.session_state.extracted_metadata = None
    st.session_state.extraction_status = 'idle'
    st.session_state.extraction_error = None
    st.session_state.tokens_used = 0


def reset_edit_state():
    """Reset edit-related state."""
    st.session_state.current_listing = None
    st.session_state.form_data = {}
    st.session_state.unsaved_changes = False


def set_workflow_step(step: int):
    """Set the current workflow step."""
    st.session_state.workflow_step = step


def record_action(action: str):
    """Record the last action taken."""
    st.session_state.last_action = action
    st.session_state.last_action_time = datetime.now().isoformat()


def get_image_groups() -> Dict[str, ImageGroup]:
    """Get all image groups."""
    return st.session_state.get('image_groups', {})


def add_image_group(name: str, images: List[str], primary: Optional[str] = None):
    """Add or update an image group."""
    if 'image_groups' not in st.session_state:
        st.session_state.image_groups = {}

    st.session_state.image_groups[name] = ImageGroup(
        name=name,
        images=images,
        primary_image=primary or (images[0] if images else None)
    )


def remove_image_group(name: str):
    """Remove an image group."""
    if name in st.session_state.get('image_groups', {}):
        del st.session_state.image_groups[name]


def get_extracted_metadata() -> Optional[Dict[str, Any]]:
    """Get extracted metadata."""
    return st.session_state.get('extracted_metadata')


def set_extracted_metadata(metadata: Dict[str, Any]):
    """Set extracted metadata."""
    st.session_state.extracted_metadata = metadata
    st.session_state.extraction_status = 'complete'


def get_form_data() -> Dict[str, Any]:
    """Get current form data."""
    return st.session_state.get('form_data', {})


def update_form_data(key: str, value: Any):
    """Update a single form field."""
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}
    st.session_state.form_data[key] = value
    st.session_state.unsaved_changes = True


def set_form_data(data: Dict[str, Any]):
    """Set entire form data."""
    st.session_state.form_data = data
    st.session_state.unsaved_changes = False


def mark_changes_saved():
    """Mark form changes as saved."""
    st.session_state.unsaved_changes = False


def has_unsaved_changes() -> bool:
    """Check if there are unsaved changes."""
    return st.session_state.get('unsaved_changes', False)


def get_selected_listings() -> List[str]:
    """Get list of selected listings for export."""
    return st.session_state.get('selected_listings', [])


def toggle_listing_selection(listing_dir: str):
    """Toggle selection of a listing."""
    selected = st.session_state.get('selected_listings', [])
    if listing_dir in selected:
        selected.remove(listing_dir)
    else:
        selected.append(listing_dir)
    st.session_state.selected_listings = selected


def select_all_listings(listings: List[str]):
    """Select all listings."""
    st.session_state.selected_listings = listings.copy()


def clear_listing_selection():
    """Clear all listing selections."""
    st.session_state.selected_listings = []


# Search state helpers
def reset_search_state():
    """Reset search-related state."""
    st.session_state.search_status = 'idle'
    st.session_state.search_queries = {}
    st.session_state.search_results = {}
    st.session_state.search_matches = {}
    st.session_state.search_accepted = {}
    st.session_state.search_rejected = {}
    st.session_state.search_pricing = None
    st.session_state.search_tokens_used = 0
    st.session_state.search_error = None


def get_search_queries() -> Dict[str, str]:
    """Get generated search queries."""
    return st.session_state.get('search_queries', {})


def set_search_queries(queries: Dict[str, str]):
    """Set generated search queries."""
    st.session_state.search_queries = queries


def get_search_matches() -> Dict[str, Any]:
    """Get search matches."""
    return st.session_state.get('search_matches', {})


def set_search_matches(matches: Dict[str, Any]):
    """Set search matches."""
    st.session_state.search_matches = matches


def accept_search_match(field_name: str):
    """Accept a search match for a field."""
    matches = st.session_state.get('search_matches', {})
    if field_name in matches:
        if 'search_accepted' not in st.session_state:
            st.session_state.search_accepted = {}
        st.session_state.search_accepted[field_name] = matches[field_name]
        # Remove from rejected if present
        if field_name in st.session_state.get('search_rejected', {}):
            del st.session_state.search_rejected[field_name]


def reject_search_match(field_name: str):
    """Reject a search match for a field."""
    matches = st.session_state.get('search_matches', {})
    if field_name in matches:
        if 'search_rejected' not in st.session_state:
            st.session_state.search_rejected = {}
        st.session_state.search_rejected[field_name] = matches[field_name]
        # Remove from accepted if present
        if field_name in st.session_state.get('search_accepted', {}):
            del st.session_state.search_accepted[field_name]


def get_accepted_matches() -> Dict[str, Any]:
    """Get all accepted search matches."""
    return st.session_state.get('search_accepted', {})


def merge_search_to_metadata():
    """Merge accepted search values into extracted_metadata."""
    extracted = st.session_state.get('extracted_metadata', {})
    if not extracted:
        return

    accepted = st.session_state.get('search_accepted', {})
    for field_name, match in accepted.items():
        value = match.get('value') if isinstance(match, dict) else match

        # Handle nested fields
        if field_name in ('publisher', 'publication_year', 'page_count',
                          'isbn_10', 'isbn_13', 'genre', 'place_of_publication'):
            if 'publication_details' not in extracted:
                extracted['publication_details'] = {}
            extracted['publication_details'][field_name] = value
        elif field_name == 'binding':
            if 'physical_details' not in extracted:
                extracted['physical_details'] = {}
            extracted['physical_details']['binding_type'] = value
        else:
            extracted[field_name] = value

    st.session_state.extracted_metadata = extracted
