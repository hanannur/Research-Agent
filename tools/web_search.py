"""
Web Search Tool for DeepResearch AI.
Primary Provider: DuckDuckGo Search (no paid API key required).
Academic Provider: Official arXiv Atom API for verified preprints and papers.
Fallback Provider: Open Web / Wikipedia REST API for resilient fallback.
Provides robust URL normalization, deduplication, evidence categorization, and timeout safeguards.
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import quote, urlparse, urlunparse
import xml.etree.ElementTree as ET

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


def categorize_source(url: str, title: str = "") -> str:
    """
    Categorizes a web source into distinct evidence categories:
    - Academic Paper / Preprint
    - Official Documentation
    - Engineering Blog / Technical Article
    - General Web
    """
    if not url:
        return "General Web"

    url_lower = url.lower()
    parsed = urlparse(url_lower)
    domain = parsed.netloc

    # 1. Academic Papers & Preprints
    academic_domains = (
        "arxiv.org",
        "openreview.net",
        "semanticscholar.org",
        "doi.org",
        "acm.org",
        "ieee.org",
        "nature.com",
        "biorxiv.org",
        "medrxiv.org",
        "sciencedirect.com",
        "springer.com",
        "ssrn.com",
        "researchgate.net",
        "aclweb.org",
        "neurips.cc",
        "icml.cc",
        "cvpr.thecvf.com",
    )
    if any(ad in domain for ad in academic_domains):
        return "Academic Paper / Preprint"

    # 2. Official Documentation & Specifications
    doc_domains = (
        "docs.",
        ".readthedocs.io",
        "github.com",
        "python.org",
        "pytorch.org",
        "huggingface.co",
        "developer.",
        "modelcontextprotocol.io",
        "langchain.com",
        "pydantic.dev",
        "kubernetes.io",
        "fastapi.tiangolo.com",
        "docker.com",
        "w3.org",
        "ietf.org",
        "peps.python.org",
        "cloud.google.com/docs",
        "aws.amazon.com/documentation",
        "learn.microsoft.com",
        "platform.openai.com",
        "docs.anthropic.com",
    )
    if any(dd in url_lower for dd in doc_domains):
        return "Official Documentation"

    # 3. Engineering Blogs & Technical Articles
    blog_indicators = (
        "medium.com",
        "dev.to",
        "substack.com",
        "github.io",
        "netflixtechblog.com",
        "eng.uber.com",
        "blog.",
        "blogs.",
        "/blog/",
        "/engineering/",
        "simonwillison.net",
        "martinfowler.com",
        "thegradient.pub",
        "distill.pub",
        "openai.com/index",
        "anthropic.com/news",
    )
    if any(bi in url_lower for bi in blog_indicators):
        return "Engineering Blog / Technical Article"

    return "General Web"


def search_arxiv(query: str, max_results: int = 3, timeout: float = 5.0) -> list[SourceRecord]:
    """
    Retrieves verified preprints from arXiv using the official public Atom API.
    Zero paid API key required. Never fabricates records.

    Args:
        query: Search keywords
        max_results: Max preprints to return
        timeout: Timeout in seconds

    Returns:
        List of verified SourceRecord items classified as Academic Paper / Preprint.
    """
    if not query or not query.strip():
        return []

    # Clean query of noisy punctuation for arXiv search syntax
    clean_q = re.sub(r"[^\w\s-]", " ", query).strip()
    words = [w for w in clean_q.split() if len(w) > 2]
    if not words:
        return []
    search_term = " AND ".join(words[:4])

    results: list[SourceRecord] = []
    url = f"http://export.arxiv.org/api/query?search_query=all:{quote(search_term)}&start=0&max_results={max_results}"

    try:
        headers = {"User-Agent": "DeepResearchAI/1.0 (Research Assistant; academic arXiv client)"}
        with httpx.Client(timeout=timeout, headers=headers) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                for entry in root.findall("atom:entry", ns):
                    title_elem = entry.find("atom:title", ns)
                    id_elem = entry.find("atom:id", ns)
                    summary_elem = entry.find("atom:summary", ns)
                    published_elem = entry.find("atom:published", ns)

                    if title_elem is None or id_elem is None:
                        continue

                    title = " ".join((title_elem.text or "").split())
                    paper_url = (id_elem.text or "").strip()
                    if paper_url.startswith("http://"):
                        paper_url = "https://" + paper_url[7:]
                    summary = " ".join((summary_elem.text or "").split()) if summary_elem is not None else ""
                    pub_date = published_elem.text[:10] if published_elem is not None and published_elem.text else None

                    if title and paper_url:
                        results.append(
                            SourceRecord(
                                title=title,
                                url=paper_url,
                                snippet=summary[:320] + ("..." if len(summary) > 320 else ""),
                                relevant_query=f"{query} (arXiv)",
                                publication_date=pub_date,
                                source_type="Academic Paper / Preprint",
                            )
                        )
    except Exception as exc:
        logger.info("arXiv query failed gracefully for '%s': %s", query, exc)

    return results


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
                                source_type=categorize_source(u, t),
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
        List of structured SourceRecord instances with evidence categorization.
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
                            source_type=categorize_source(url, title),
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
    include_academic: bool = True,
) -> tuple[list[SourceRecord], list[str]]:
    """
    Executes a batch of search queries with deduplication by normalized URL.
    Optionally retrieves verified academic preprints via arXiv for technical/scientific queries.

    Args:
        queries: List of search queries
        max_results_per_query: Results per query
        max_total_sources: Hard limit on total deduplicated sources
        ddgs_client: Optional injected DDGS instance for testing
        delay_between_calls: Pause between queries
        include_academic: Whether to check public arXiv API for relevant preprints

    Returns:
        (deduplicated_sources, failed_queries)
    """
    unique_sources: list[SourceRecord] = []
    seen_urls: set[str] = set()
    failed_queries: list[str] = []

    # 1. Execute targeted queries
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

    # 2. Complement with real academic preprints from arXiv if space permits and not mocked
    if include_academic and ddgs_client is None and len(unique_sources) < max_total_sources and queries:
        try:
            primary_topic = queries[0]
            arxiv_records = search_arxiv(primary_topic, max_results=2)
            for arec in arxiv_records:
                norm_url = normalize_url(arec.url)
                if norm_url and norm_url not in seen_urls:
                    seen_urls.add(norm_url)
                    unique_sources.append(arec)
                    if len(unique_sources) >= max_total_sources:
                        break
        except Exception as e:
            logger.debug("Academic preprint enrichment skipped: %s", e)

    return unique_sources, failed_queries
