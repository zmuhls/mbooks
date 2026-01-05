"""Book Lister - Streamlit GUI for collectible book management.

Main entry point for the Streamlit application. Provides a web-based interface
for uploading book images, extracting metadata via AI, editing listings, and
exporting to eBay CSV format.

Usage:
    streamlit run src/gui/app.py
    # or
    make gui
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.gui.state import init_session_state


def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(
        page_title="Book Lister",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Initialize session state
    init_session_state()

    # Hide sidebar completely + minimal custom CSS
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="stSidebarCollapsedControl"] { display: none; }
        .title-preview {
            font-family: monospace;
            padding: 10px;
            background-color: #f5f5f5;
            border-radius: 5px;
            border-left: 4px solid #1e3a5f;
        }
        .title-good { border-left-color: #2e7d32; }
        .title-warning { border-left-color: #f9a825; }
        .title-danger { border-left-color: #c62828; }
        </style>
    """, unsafe_allow_html=True)

    # Header
    st.title("📚 Book Lister")
    st.caption("Collectible book management for eBay sellers")
    st.divider()

    # Main navigation tabs
    tabs = st.tabs([
        "📤 Upload",
        "🔍 Extract",
        "🌐 Search",
        "✏️ Edit",
        "📖 Library",
        "📦 Export"
    ])

    with tabs[0]:
        from src.gui.pages import upload
        upload.render()

    with tabs[1]:
        from src.gui.pages import extract
        extract.render()

    with tabs[2]:
        from src.gui.pages import search
        search.render()

    with tabs[3]:
        from src.gui.pages import edit
        edit.render()

    with tabs[4]:
        from src.gui.pages import library
        library.render()

    with tabs[5]:
        from src.gui.pages import export
        export.render()


if __name__ == "__main__":
    main()
