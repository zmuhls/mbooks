"""Search providers for web-based metadata enrichment.

Supports multiple search APIs:
- OpenRouter (primary) - Uses existing API key with web-search capable models
- Perplexity Sonar (alternative) - AI-powered web search with synthesis
- SerpAPI (fallback) - Direct Google search results
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a single search result."""
    title: str
    url: str
    snippet: str
    source: str  # 'ebay', 'abebooks', 'amazon', etc.
    raw_data: Dict[str, Any]


@dataclass
class SearchResponse:
    """Response from a search provider."""
    query: str
    results: List[SearchResult]
    synthesized_answer: Optional[str]  # AI-generated summary
    citations: List[str]
    tokens_used: int
    provider: str


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> SearchResponse:
        """Execute a search query.

        Args:
            query: Search query string
            num_results: Maximum number of results

        Returns:
            SearchResponse with results
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        pass


class OpenRouterProvider(SearchProvider):
    """OpenRouter API provider with web search capability.

    Uses OpenRouter with Perplexity's online models for web search,
    leveraging the existing OPENROUTER_API_KEY.
    """

    SYSTEM_PROMPT = """You are a research assistant specializing in rare and collectible books.
When searching for book information, extract and return structured data including:
- Publisher name and location (city, state/country)
- ISBN-10 and ISBN-13
- Page count
- Publication year
- Edition details (limited edition size, signed status)
- Comparable sales prices from eBay completed listings
- Condition language used in successful listings

Return information in a structured JSON format when possible.
Always cite your sources with URLs when available."""

    def __init__(self, api_key: Optional[str] = None, model: str = "perplexity/sonar:online"):
        """Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            model: Model to use (default: perplexity/sonar:online for web search)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

    def is_configured(self) -> bool:
        """Check if API key is available."""
        return bool(self.api_key)

    def get_name(self) -> str:
        return "openrouter"

    def search(self, query: str, num_results: int = 10) -> SearchResponse:
        """Execute search using OpenRouter with Perplexity model.

        Args:
            query: Search query string
            num_results: Not directly used (model synthesizes results)

        Returns:
            SearchResponse with synthesized answer and citations
        """
        if not self.is_configured():
            raise ValueError("OPENROUTER_API_KEY not configured")

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0

            # Extract citations from response text
            citations = self._extract_citations(content)

            # Parse results from response
            results = self._parse_results(content, citations)

            return SearchResponse(
                query=query,
                results=results,
                synthesized_answer=content,
                citations=citations,
                tokens_used=tokens,
                provider=self.get_name()
            )

        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
        except Exception as e:
            log.error(f"OpenRouter search failed: {e}")
            raise

    def _extract_citations(self, content: str) -> List[str]:
        """Extract URLs from response content.

        Args:
            content: Response text

        Returns:
            List of URLs found
        """
        import re
        # Find URLs in the response
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        # Deduplicate while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            # Clean trailing punctuation
            url = url.rstrip('.,;:)')
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        return unique_urls

    def _parse_results(self, content: str, citations: List[str]) -> List[SearchResult]:
        """Parse search results from response content.

        Args:
            content: Response text
            citations: List of citation URLs

        Returns:
            List of SearchResult objects
        """
        results = []

        # Create results from citations
        for i, url in enumerate(citations):
            source = self._identify_source(url)
            results.append(SearchResult(
                title=f"Source {i + 1}",
                url=url,
                snippet="",
                source=source,
                raw_data={"citation_index": i}
            ))

        return results

    def _identify_source(self, url: str) -> str:
        """Identify source type from URL.

        Args:
            url: URL string

        Returns:
            Source identifier
        """
        url_lower = url.lower()
        if 'ebay.com' in url_lower:
            return 'ebay'
        elif 'abebooks.com' in url_lower:
            return 'abebooks'
        elif 'amazon.com' in url_lower:
            return 'amazon'
        elif 'worldcat.org' in url_lower:
            return 'worldcat'
        elif 'goodreads.com' in url_lower:
            return 'goodreads'
        return 'web'

    def search_for_fields(
        self,
        metadata: Dict[str, Any],
        target_fields: List[str]
    ) -> SearchResponse:
        """Search specifically for missing metadata fields.

        Args:
            metadata: Current book metadata
            target_fields: List of fields to find

        Returns:
            SearchResponse with targeted results
        """
        # Build a targeted query
        title = metadata.get('title') or metadata.get('basic_info', {}).get('title', '')
        author = metadata.get('author') or metadata.get('basic_info', {}).get('author', '')

        query_parts = [f'Find the following information for the book "{title}"']
        if author:
            query_parts.append(f'by {author}')
        query_parts.append(':')

        field_descriptions = {
            'publisher': 'Publisher name and location (city, state)',
            'isbn': 'ISBN-10 and ISBN-13',
            'page_count': 'Number of pages',
            'publication_year': 'Year of publication',
            'genre': 'Genre/Subject category',
            'binding': 'Binding type (Hardcover, etc.)',
            'comparable_prices': 'Recent eBay sold prices for similar copies',
        }

        for field in target_fields:
            if field in field_descriptions:
                query_parts.append(f'- {field_descriptions[field]}')

        query = ' '.join(query_parts)
        return self.search(query)


class PerplexityProvider(SearchProvider):
    """Perplexity Sonar API provider (direct).

    Uses Perplexity's API directly. Requires PERPLEXITY_API_KEY.
    """

    SYSTEM_PROMPT = """You are a research assistant specializing in rare and collectible books.
When searching for book information, extract and return structured data including:
- Publisher name and location (city, state/country)
- ISBN-10 and ISBN-13
- Page count
- Publication year
- Edition details (limited edition size, signed status)
- Comparable sales prices from eBay completed listings
- Condition language used in successful listings

Return information in a structured JSON format when possible.
Always cite your sources with URLs."""

    def __init__(self, api_key: Optional[str] = None, model: str = "sonar"):
        """Initialize Perplexity provider.

        Args:
            api_key: Perplexity API key (defaults to PERPLEXITY_API_KEY env var)
            model: Model to use ('sonar' or 'sonar-pro')
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.model = model
        self.base_url = "https://api.perplexity.ai"

    def is_configured(self) -> bool:
        """Check if API key is available."""
        return bool(self.api_key)

    def get_name(self) -> str:
        return "perplexity"

    def search(self, query: str, num_results: int = 10) -> SearchResponse:
        """Execute search using Perplexity Sonar API."""
        if not self.is_configured():
            raise ValueError("PERPLEXITY_API_KEY not configured")

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0

            citations = []
            if hasattr(response, 'citations') and response.citations:
                citations = response.citations

            results = self._parse_results(content, citations)

            return SearchResponse(
                query=query,
                results=results,
                synthesized_answer=content,
                citations=citations,
                tokens_used=tokens,
                provider=self.get_name()
            )

        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
        except Exception as e:
            log.error(f"Perplexity search failed: {e}")
            raise

    def _parse_results(self, content: str, citations: List[str]) -> List[SearchResult]:
        """Parse search results from response content."""
        results = []
        for i, url in enumerate(citations):
            source = self._identify_source(url)
            results.append(SearchResult(
                title=f"Citation {i + 1}",
                url=url,
                snippet="",
                source=source,
                raw_data={"citation_index": i}
            ))
        return results

    def _identify_source(self, url: str) -> str:
        """Identify source type from URL."""
        url_lower = url.lower()
        if 'ebay.com' in url_lower:
            return 'ebay'
        elif 'abebooks.com' in url_lower:
            return 'abebooks'
        elif 'amazon.com' in url_lower:
            return 'amazon'
        elif 'worldcat.org' in url_lower:
            return 'worldcat'
        elif 'goodreads.com' in url_lower:
            return 'goodreads'
        return 'web'


class SerpAPIProvider(SearchProvider):
    """SerpAPI provider for direct Google search results.

    Fallback provider when Perplexity is unavailable.
    Returns raw search results without AI synthesis.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize SerpAPI provider.

        Args:
            api_key: SerpAPI key (defaults to SERPAPI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")

    def is_configured(self) -> bool:
        """Check if API key is available."""
        return bool(self.api_key)

    def get_name(self) -> str:
        return "serpapi"

    def search(self, query: str, num_results: int = 10) -> SearchResponse:
        """Execute Google search via SerpAPI.

        Args:
            query: Search query string
            num_results: Maximum number of results

        Returns:
            SearchResponse with search results
        """
        if not self.is_configured():
            raise ValueError("SERPAPI_API_KEY not configured")

        try:
            import serpapi

            client = serpapi.Client(api_key=self.api_key)
            search_results = client.search({
                "q": query,
                "engine": "google",
                "num": num_results
            })

            results = []
            for item in search_results.get("organic_results", []):
                source = self._identify_source(item.get("link", ""))
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source=source,
                    raw_data=item
                ))

            return SearchResponse(
                query=query,
                results=results,
                synthesized_answer=None,
                citations=[r.url for r in results],
                tokens_used=0,
                provider=self.get_name()
            )

        except ImportError:
            raise ImportError("serpapi package required. Install with: pip install google-search-results")
        except Exception as e:
            log.error(f"SerpAPI search failed: {e}")
            raise

    def _identify_source(self, url: str) -> str:
        """Identify source type from URL."""
        url_lower = url.lower()
        if 'ebay.com' in url_lower:
            return 'ebay'
        elif 'abebooks.com' in url_lower:
            return 'abebooks'
        elif 'amazon.com' in url_lower:
            return 'amazon'
        return 'web'


def get_search_provider(provider_name: Optional[str] = None) -> SearchProvider:
    """Get a configured search provider.

    Args:
        provider_name: Optional provider name ('openrouter', 'perplexity', 'serpapi')
                      If not specified, returns first available provider.

    Returns:
        Configured SearchProvider instance

    Raises:
        ValueError: If no providers are configured
    """
    providers = {
        'openrouter': OpenRouterProvider,
        'perplexity': PerplexityProvider,
        'serpapi': SerpAPIProvider,
    }

    if provider_name:
        if provider_name not in providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        provider = providers[provider_name]()
        if not provider.is_configured():
            raise ValueError(f"Provider {provider_name} not configured (missing API key)")
        return provider

    # Auto-select first available (OpenRouter first since user has that key)
    for name, provider_class in providers.items():
        provider = provider_class()
        if provider.is_configured():
            log.info(f"Using search provider: {name}")
            return provider

    raise ValueError("No search providers configured. Set OPENROUTER_API_KEY, PERPLEXITY_API_KEY, or SERPAPI_API_KEY")


def search_with_fallback(query: str, num_results: int = 10) -> Optional[SearchResponse]:
    """Search with automatic provider fallback.

    Tries providers in order until one succeeds.

    Args:
        query: Search query string
        num_results: Maximum results

    Returns:
        SearchResponse or None if all providers fail
    """
    provider_order = ['perplexity', 'serpapi']

    for provider_name in provider_order:
        try:
            provider_class = {'perplexity': PerplexityProvider, 'serpapi': SerpAPIProvider}[provider_name]
            provider = provider_class()

            if not provider.is_configured():
                continue

            return provider.search(query, num_results)

        except Exception as e:
            log.warning(f"{provider_name} failed: {e}")
            continue

    log.error("All search providers failed")
    return None
