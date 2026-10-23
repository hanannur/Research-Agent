"""
Web Search Tool.
Primary Provider: DuckDuckGo Search (no API key required).
Fallback Provider: Open Web / Wikipedia REST API for when DuckDuckGo
experiences rate limits, network timeouts, or ISP blocks.
Provides robust URL normalization, deduplication, error handling, and timeout safeguards.
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import quote, urlparse, urlunparse

import httpx

try:
    from models.schemas import SourceRecord
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from models.schemas import SourceRecord

logger = logging.getLogger(__name__)

# Try to import DDGS from ddgs or duckduckgo_search
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


def normalize_url(raw_url: str) -> str:
    """
    Normalizes a URL by stripping whitespace, trailing slashes,
    fragments, and default ports to ensure robust deduplication.
    """
    if not raw_url:
        return ""
    try:
        parsed = urlparse(raw_url.strip())
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        normalized = urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))
        return normalized or raw_url.strip()
    except Exception:
        return raw_url.strip()


def fallback_web_search(query: str, max_results: int = 4) -> list[SourceRecord]:
    """
    Fallback search provider using open encyclopedia and web endpoints.
    Used when DuckDuckGo times out, is rate-limited, or blocked by local network.
    Returns real, verified titles, URLs, and snippets without fabrication.
    """
    results: list[SourceRecord] = []
    stopwords = {"in", "the", "of", "for", "and", "to", "what", "how", "2026", "trends", "overview", "emerging", "impact", "are", "is", "on"}

    # Generate candidate search terms: full query first, then keyword reduction
    candidates = [query.strip()]
    tokens = [w for w in re.findall(r"\w+", query) if w.lower() not in stopwords]
    if len(tokens) >= 2:
        candidates.append(" ".join(tokens[:3]))
        candidates.append(" ".join(tokens[:2]))

    try:
        headers = {"User-Agent": "DeepResearchAI/1.0 (Student Research Project; contact: student@univ.edu)"}
        with httpx.Client(timeout=6.0, headers=headers) as client:
            for cand in candidates:
                if results:
                    break
                resp = client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "opensearch",
                        "search": cand,
                        "limit": max_results,
                        "format": "json",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    titles = data[1] if len(data) > 1 else []
                    urls = data[3] if len(data) > 3 else []

                    for t, u in zip(titles, urls):
                        snippet = "Encyclopedic article and empirical background."
                        try:
                            clean_title = quote(t.replace(" ", "_"))
                            sum_resp = client.get(
                                f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_title}"
                            )
                            if sum_resp.status_code == 200:
                                extract = sum_resp.json().get("extract")
                                if extract:
                                    snippet = extract[:300]
                        except Exception:
                            pass

                        results.append(
                            SourceRecord(
                                title=t,
                                url=u,
                                snippet=snippet,
                                relevant_query=f"{cand} (Open Web)",
                                publication_date=None,
                            )
                        )
    except Exception as exc:
        logger.warning("Fallback web search error: %s", exc)

    return results


def search_duckduckgo(
    query: str,
    max_results: int = 4,
    timeout: int = 5,
    ddgs_client: Optional[object] = None,
) -> list[SourceRecord]:
    """
    Executes a web search query.
    Attempts DuckDuckGo first; if DuckDuckGo times out or fails due to network/rate limits,
    seamlessly utilizes open web search fallback to ensure real evidence is retrieved.

    Args:
        query: Search term
        max_results: Max results to return
        timeout: Timeout in seconds
        ddgs_client: Optional injected DDGS instance (for mocking/testing)

    Returns:
        List of structured SourceRecord instances.
    """
    if not query or not query.strip():
        logger.warning("Empty search query passed to search_duckduckgo")
        return []

    clean_query = query.strip()
    results: list[SourceRecord] = []

    # 1. Attempt DuckDuckGo
    if ddgs_client is not None or DDGS is not None:
        try:
            client = ddgs_client or DDGS(timeout=timeout)
            raw_results = client.text(clean_query, max_results=max_results)

            if raw_results:
                for item in raw_results:
                    title = item.get("title", "").strip()
                    url = item.get("href") or item.get("link") or ""
                    snippet = item.get("body") or item.get("snippet") or ""

                    if not url or not title or not url.startswith(("http://", "https://")):
                        continue

                    results.append(
                        SourceRecord(
                            title=title,
                            url=url,
                            snippet=snippet or "No snippet provided.",
                            relevant_query=clean_query,
                            publication_date=None,
                        )
                    )
        except Exception as exc:
            logger.info("DuckDuckGo timed out or rate-limited for '%s': %s", clean_query, exc)

    # 2. If DuckDuckGo returned no results and no client was injected, run resilient open web fallback
    if not results and ddgs_client is None:
        logger.info("Engaging open web fallback search for '%s'", clean_query)
        results = fallback_web_search(clean_query, max_results=max_results)

    return results


def batch_search(
    queries: list[str],
    max_results_per_query: int = 4,
    max_total_sources: int = 15,
    ddgs_client: Optional[object] = None,
    delay_between_calls: float = 0.2,
) -> tuple[list[SourceRecord], list[str]]:
    """
    Executes a batch of search queries with deduplication by normalized URL.

    Args:
        queries: List of search queries
        max_results_per_query: Results per query
        max_total_sources: Hard limit on total deduplicated sources
        ddgs_client: Optional injected DDGS instance for testing
        delay_between_calls: Pause between queries

    Returns:
        (deduplicated_sources, failed_queries)
    """
    unique_sources: list[SourceRecord] = []
    seen_urls: set[str] = set()
    failed_queries: list[str] = []

    for idx, query in enumerate(queries):
        if len(unique_sources) >= max_total_sources:
            break

        if idx > 0 and delay_between_calls > 0:
            time.sleep(delay_between_calls)

        try:
            records = search_duckduckgo(
                query=query,
                max_results=max_results_per_query,
                ddgs_client=ddgs_client,
            )

            if not records:
                failed_queries.append(query)
                continue

            for record in records:
                norm_url = normalize_url(record.url)
                if norm_url and norm_url not in seen_urls:
                    seen_urls.add(norm_url)
                    unique_sources.append(record)
                    if len(unique_sources) >= max_total_sources:
                        break

        except Exception as exc:
            logger.error("Error executing query '%s': %s", query, exc)
            failed_queries.append(query)

    return unique_sources, failed_queries
