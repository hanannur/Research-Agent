"""
Unit tests for DuckDuckGo web search tool and normalization logic.
All tests use mocked DDGS clients to run reliably without live network access.
"""

from unittest.mock import MagicMock

from tools.web_search import batch_search, normalize_url, search_duckduckgo


def test_normalize_url():
    """Tests URL normalization and stripping of query fragments/trailing slashes."""
    assert (
        normalize_url("https://example.com/path/")
        == "https://example.com/path"
    )
    assert (
        normalize_url("https://example.com/path#section")
        == "https://example.com/path"
    )
    assert (
        normalize_url("HTTPS://Example.COM/Path")
        == "https://example.com/Path"
    )
    assert normalize_url("") == ""


def test_search_duckduckgo_with_mock():
    """Tests search_duckduckgo with a mocked DDGS client returning results."""
    mock_ddgs = MagicMock()
    mock_ddgs.text.return_value = [
        {
            "title": "AI in 2026",
            "href": "https://example.com/ai-2026",
            "body": "A comprehensive review of AI trends.",
        },
        {
            "title": "Invalid Scheme",
            "href": "javascript:alert(1)",
            "body": "Ignored.",
        },
    ]

    records = search_duckduckgo("AI trends", max_results=5, ddgs_client=mock_ddgs)
    assert len(records) == 1
    assert records[0].title == "AI in 2026"
    assert records[0].url == "https://example.com/ai-2026"
    assert records[0].snippet == "A comprehensive review of AI trends."


def test_search_duckduckgo_empty_results():
    """Tests behavior when search returns empty list."""
    mock_ddgs = MagicMock()
    mock_ddgs.text.return_value = []

    records = search_duckduckgo("Unknown query", ddgs_client=mock_ddgs)
    assert records == []


def test_search_duckduckgo_exception_handling():
    """Tests that search exceptions are caught gracefully and return empty list."""
    mock_ddgs = MagicMock()
    mock_ddgs.text.side_effect = TimeoutError("Connection to DuckDuckGo timed out")

    records = search_duckduckgo("Timeout query", ddgs_client=mock_ddgs)
    assert records == []


def test_batch_search_deduplication():
    """Tests that batch_search deduplicates identical or equivalent URLs."""
    mock_ddgs = MagicMock()
    # First query returns URL A and B
    # Second query returns URL A (with trailing slash) and C
    mock_ddgs.text.side_effect = [
        [
            {"title": "Doc A", "href": "https://example.com/doc", "body": "Snippet A"},
            {"title": "Doc B", "href": "https://example.com/b", "body": "Snippet B"},
        ],
        [
            {"title": "Doc A Dupe", "href": "https://example.com/doc/", "body": "Snippet A2"},
            {"title": "Doc C", "href": "https://example.com/c", "body": "Snippet C"},
        ],
    ]

    sources, failed = batch_search(
        queries=["q1", "q2"],
        max_results_per_query=5,
        ddgs_client=mock_ddgs,
        delay_between_calls=0.0,
    )

    assert len(sources) == 3
    urls = [s.url for s in sources]
    assert "https://example.com/doc" in urls
    assert "https://example.com/b" in urls
    assert "https://example.com/c" in urls
    assert len(failed) == 0
