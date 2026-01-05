"""Search module for enriching book metadata via web search.

This module provides:
- Query generation for eBay, AbeBooks, and bibliographic sources
- OpenRouter/Perplexity API integration for web search
- Result parsing and field matching with confidence scoring
"""

from .query_builder import SearchQueryBuilder
from .providers import OpenRouterProvider, PerplexityProvider, get_search_provider

__all__ = [
    'SearchQueryBuilder',
    'OpenRouterProvider',
    'PerplexityProvider',
    'get_search_provider',
]
