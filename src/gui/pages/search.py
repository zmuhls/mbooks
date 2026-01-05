"""Search page - Web search for metadata enrichment.

Uses Perplexity Sonar API to search eBay completed listings and bibliographic
sources to fill in missing metadata fields.
"""

import streamlit as st
import os
from typing import Dict, Any, List, Optional

from src.gui.state import (
    get_extracted_metadata,
    set_extracted_metadata,
    get_search_queries,
    set_search_queries,
    get_search_matches,
    set_search_matches,
    accept_search_match,
    reject_search_match,
    get_accepted_matches,
    merge_search_to_metadata,
    reset_search_state,
    set_workflow_step,
    record_action
)


def render():
    """Render the search page."""
    st.header("Search & Enrich")

    # Check prerequisites
    extracted = get_extracted_metadata()
    if not extracted:
        st.warning("No extracted metadata. Please complete the **Extract** step first.")
        if st.button("Go to Extract"):
            set_workflow_step(1)
            st.rerun()
        return

    # Check API key (OpenRouter or Perplexity)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    if not openrouter_key and not perplexity_key:
        st.error("No search API key configured.")
        st.markdown("""
        **Setup required (choose one):**

        **Option 1 - OpenRouter (recommended, uses existing key):**
        - Uses `perplexity/sonar:online` model with web search
        - Add to `.env`: `OPENROUTER_API_KEY=sk-or-...`

        **Option 2 - Perplexity Direct:**
        - Get key from [Perplexity](https://www.perplexity.ai/settings/api)
        - Add to `.env`: `PERPLEXITY_API_KEY=pplx-...`
        """)

        # Allow skip
        if st.button("Skip Search (proceed to Edit)", type="secondary"):
            set_workflow_step(3)
            st.rerun()
        return

    # Main layout
    col1, col2 = st.columns([1, 1])

    with col1:
        render_metadata_summary(extracted)

    with col2:
        render_missing_fields(extracted)

    st.divider()

    # Query section
    render_query_section(extracted)

    st.divider()

    # Results section
    render_results_section()

    st.divider()

    # Navigation
    render_navigation()


def render_metadata_summary(metadata: Dict[str, Any]):
    """Display current metadata summary."""
    st.subheader("Current Metadata")

    # Basic info
    basic = metadata.get('basic_info', {})
    title = basic.get('title') or metadata.get('title', 'Unknown')
    author = basic.get('author') or metadata.get('author')
    editor = basic.get('editor') or metadata.get('editor')

    st.markdown(f"**Title:** {title}")
    if author:
        st.markdown(f"**Author:** {author}")
    if editor:
        st.markdown(f"**Editor:** {editor}")

    # Edition info
    edition = metadata.get('edition_details', {})
    if edition.get('is_signed') or metadata.get('is_signed'):
        st.success("Signed")
    if edition.get('is_limited_edition') or metadata.get('is_limited_edition'):
        size = edition.get('edition_size') or metadata.get('edition_size')
        if size:
            st.info(f"Limited Edition ({size} copies)")
        else:
            st.info("Limited Edition")


def render_missing_fields(metadata: Dict[str, Any]) -> List[str]:
    """Display missing fields that can be searched."""
    st.subheader("Missing Fields")

    missing = identify_missing_fields(metadata)

    if not missing:
        st.success("All required fields populated!")
        return []

    for field in missing:
        field_display = {
            'publisher': 'Publisher',
            'place_of_publication': 'Place of Publication',
            'isbn_10': 'ISBN-10',
            'isbn_13': 'ISBN-13',
            'page_count': 'Page Count',
            'publication_year': 'Publication Year',
            'genre': 'Genre/Subject',
            'binding': 'Binding Type',
        }.get(field, field)
        st.markdown(f"- {field_display}")

    return missing


def identify_missing_fields(metadata: Dict[str, Any]) -> List[str]:
    """Identify fields that are missing or empty."""
    target_fields = {
        'publisher': ['publication_details.publisher', 'publisher'],
        'place_of_publication': ['publication_details.place_of_publication', 'place_of_publication'],
        'isbn_10': ['publication_details.isbn_10', 'isbn_10'],
        'isbn_13': ['publication_details.isbn_13', 'isbn_13'],
        'page_count': ['publication_details.page_count', 'page_count'],
        'publication_year': ['publication_details.publication_year', 'publication_year'],
        'genre': ['publication_details.genre', 'genre'],
        'binding': ['physical_details.binding_type', 'binding_type', 'binding'],
    }

    missing = []
    for field_name, paths in target_fields.items():
        found = False
        for path in paths:
            value = get_nested_value(metadata, path)
            if value:
                found = True
                break
        if not found:
            missing.append(field_name)

    return missing


def get_nested_value(data: Dict, path: str) -> Any:
    """Get nested value using dot notation."""
    keys = path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value


def render_query_section(metadata: Dict[str, Any]):
    """Render query generation and execution section."""
    st.subheader("Search Queries")

    # Generate queries if not already done
    queries = get_search_queries()
    if not queries:
        queries = generate_queries(metadata)
        set_search_queries(queries)

    # Display queries with edit capability
    for query_type, query_text in queries.items():
        query_label = {
            'ebay_completed': 'eBay Completed Listings',
            'bibliographic': 'Bibliographic Search',
            'abebooks': 'AbeBooks',
            'amazon': 'Amazon',
        }.get(query_type, query_type)

        with st.expander(f"{query_label}", expanded=query_type == 'ebay_completed'):
            # Editable query
            edited_query = st.text_area(
                "Query",
                value=query_text,
                key=f"query_{query_type}",
                height=80,
                label_visibility="collapsed"
            )

            # Update if changed
            if edited_query != query_text:
                queries[query_type] = edited_query
                set_search_queries(queries)

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"Run", key=f"run_{query_type}"):
                    run_search(query_type, edited_query)
            with col2:
                # Copy button using clipboard
                st.code(edited_query, language=None)

    # Run all button
    st.divider()
    if st.button("Run All Searches", type="primary", use_container_width=True):
        run_all_searches(queries)


def generate_queries(metadata: Dict[str, Any]) -> Dict[str, str]:
    """Generate search queries from metadata."""
    try:
        from src.search.query_builder import SearchQueryBuilder

        builder = SearchQueryBuilder(metadata)
        queries = {}

        # eBay completed listing query
        ebay_query = builder.build_ebay_query()
        if ebay_query:
            queries['ebay_completed'] = ebay_query.query_text

        # Bibliographic query
        biblio_query = builder.build_bibliographic_query()
        if biblio_query:
            queries['bibliographic'] = biblio_query.query_text

        return queries

    except ImportError as e:
        st.error(f"Could not import search module: {e}")
        return {}


def run_search(query_type: str, query_text: str):
    """Run a single search query."""
    st.session_state.search_status = 'searching'

    try:
        from src.search.providers import get_search_provider
        from src.search.result_parser import SearchResultParser
        from src.search.field_matcher import FieldMatcher

        with st.spinner(f"Searching {query_type}..."):
            # Get provider (auto-selects OpenRouter if available)
            provider = get_search_provider()

            # Execute search
            response = provider.search(query_text)

            # Track tokens
            st.session_state.search_tokens_used += response.tokens_used

            # Parse results
            parser = SearchResultParser()
            parsed_fields = parser.parse_synthesized_answer(
                response.synthesized_answer or '',
                source=query_type
            )

            # Match fields
            matcher = FieldMatcher()
            extracted = get_extracted_metadata() or {}
            match_result = matcher.match_fields(parsed_fields, extracted)

            # Store results
            existing_matches = get_search_matches()
            for field_name, match in match_result.matches.items():
                # Convert FieldMatch to dict for storage
                existing_matches[field_name] = {
                    'value': match.value,
                    'confidence': match.confidence,
                    'source': match.source_url,
                    'source_type': match.source_type,
                    'reasoning': match.reasoning,
                    'auto_accepted': match.auto_accepted,
                }

                # Auto-accept high confidence
                if match.auto_accepted:
                    accept_search_match(field_name)

            set_search_matches(existing_matches)

            # Store pricing if available
            if match_result.pricing:
                st.session_state.search_pricing = {
                    'min': match_result.pricing.min_price,
                    'max': match_result.pricing.max_price,
                    'avg': match_result.pricing.avg_price,
                    'recent': match_result.pricing.recent_price,
                    'num_sales': match_result.pricing.num_sales,
                }

            # Store raw response
            if 'search_results' not in st.session_state:
                st.session_state.search_results = {}
            st.session_state.search_results[query_type] = {
                'answer': response.synthesized_answer,
                'citations': response.citations,
            }

            st.session_state.search_status = 'complete'
            st.success(f"Found {len(match_result.matches)} field(s)")
            st.rerun()

    except Exception as e:
        st.session_state.search_status = 'error'
        st.session_state.search_error = str(e)
        st.error(f"Search failed: {e}")


def run_all_searches(queries: Dict[str, str]):
    """Run all generated queries."""
    for query_type, query_text in queries.items():
        run_search(query_type, query_text)


def render_results_section():
    """Render search results with accept/reject buttons."""
    st.subheader("Search Results")

    matches = get_search_matches()
    accepted = get_accepted_matches()
    rejected = st.session_state.get('search_rejected', {})

    if not matches:
        status = st.session_state.get('search_status', 'idle')
        if status == 'idle':
            st.info("Run a search to find missing metadata")
        elif status == 'searching':
            st.info("Searching...")
        elif status == 'error':
            error = st.session_state.get('search_error', 'Unknown error')
            st.error(f"Search error: {error}")
        return

    # Display each match
    for field_name, match in matches.items():
        is_accepted = field_name in accepted
        is_rejected = field_name in rejected

        field_display = {
            'publisher': 'Publisher',
            'place_of_publication': 'Place of Publication',
            'isbn_10': 'ISBN-10',
            'isbn_13': 'ISBN-13',
            'page_count': 'Page Count',
            'publication_year': 'Publication Year',
            'genre': 'Genre/Subject',
            'binding': 'Binding Type',
        }.get(field_name, field_name)

        # Card-like container
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 2])

            with col1:
                st.markdown(f"**{field_display}**")
                st.markdown(f"Value: `{match['value']}`")

            with col2:
                confidence = match.get('confidence', 0)
                confidence_pct = int(confidence * 100)

                # Color based on confidence
                if confidence >= 0.95:
                    st.success(f"{confidence_pct}%")
                elif confidence >= 0.80:
                    st.info(f"{confidence_pct}%")
                elif confidence >= 0.70:
                    st.warning(f"{confidence_pct}%")
                else:
                    st.error(f"{confidence_pct}%")

            with col3:
                if is_accepted:
                    st.success("Accepted")
                    if st.button("Undo", key=f"undo_{field_name}"):
                        reject_search_match(field_name)
                        st.rerun()
                elif is_rejected:
                    st.error("Rejected")
                    if st.button("Reconsider", key=f"reconsider_{field_name}"):
                        # Remove from rejected
                        del st.session_state.search_rejected[field_name]
                        st.rerun()
                else:
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("Accept", key=f"accept_{field_name}", type="primary"):
                            accept_search_match(field_name)
                            st.rerun()
                    with btn_col2:
                        if st.button("Reject", key=f"reject_{field_name}"):
                            reject_search_match(field_name)
                            st.rerun()

            # Source info
            source = match.get('source', '')
            reasoning = match.get('reasoning', '')
            st.caption(f"Source: {reasoning}")

            st.divider()

    # Pricing section
    pricing = st.session_state.get('search_pricing')
    if pricing:
        st.subheader("Comparable Prices")
        col1, col2, col3 = st.columns(3)
        with col1:
            if pricing.get('min') and pricing.get('max'):
                st.metric("Range", f"${pricing['min']:.0f} - ${pricing['max']:.0f}")
        with col2:
            if pricing.get('avg'):
                st.metric("Average", f"${pricing['avg']:.0f}")
        with col3:
            if pricing.get('num_sales'):
                st.metric("# Sales", pricing['num_sales'])

        st.caption("Pricing shown for guidance only - set your own price in the Export step")

    # Token usage
    tokens = st.session_state.get('search_tokens_used', 0)
    if tokens:
        st.caption(f"API tokens used: {tokens:,}")


def render_navigation():
    """Render navigation buttons."""
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("Back to Extract", use_container_width=True):
            set_workflow_step(1)
            st.rerun()

    with col2:
        if st.button("Reset Search", use_container_width=True):
            reset_search_state()
            st.rerun()

    with col3:
        accepted_count = len(get_accepted_matches())
        btn_label = f"Continue to Edit ({accepted_count} fields)" if accepted_count else "Skip to Edit"

        if st.button(btn_label, type="primary", use_container_width=True):
            # Merge accepted values into metadata
            if accepted_count:
                merge_search_to_metadata()
                record_action("search_complete")

            set_workflow_step(3)
            st.rerun()
