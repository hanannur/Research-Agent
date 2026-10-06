"""
Tests for DeepResearch AI specialization, source categorization, and academic retrieval.
"""

from unittest.mock import MagicMock, patch
import pytest

from models.schemas import ResearchPlan, SourceRecord
from tools.web_search import categorize_source, search_arxiv


def test_categorize_source_types():
    """Verifies that categorize_source distinguishes academic, documentation, blog, and web sources."""
    # Academic
    assert categorize_source("https://arxiv.org/abs/2307.03172") == "Academic Paper / Preprint"
    assert categorize_source("https://openreview.net/forum?id=123") == "Academic Paper / Preprint"
    assert categorize_source("https://www.semanticscholar.org/paper/abc") == "Academic Paper / Preprint"

    # Official Documentation
    assert categorize_source("https://docs.anthropic.com/en/docs/agents") == "Official Documentation"
    assert categorize_source("https://github.com/pydantic/pydantic-ai") == "Official Documentation"
    assert categorize_source("https://python.org/dev/peps/pep-0008/") == "Official Documentation"
    assert categorize_source("https://pydantic.dev") == "Official Documentation"

    # Engineering Blogs
    assert categorize_source("https://netflixtechblog.com/building-ai-agents") == "Engineering Blog / Technical Article"
    assert categorize_source("https://dev.to/engineer/rag-benchmarks") == "Engineering Blog / Technical Article"
    assert categorize_source("https://medium.com/@researcher/llm-systems") == "Engineering Blog / Technical Article"

    # General Web
    assert categorize_source("https://news.ycombinator.com/item?id=1") == "General Web"
    assert categorize_source("") == "General Web"


def test_search_arxiv_parsing():
    """Tests search_arxiv parsing of Atom XML responses without live network."""
    sample_atom_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>http://arxiv.org/abs/2401.00001v1</id>
            <title>Multi-Agent Architectures for Software Engineering</title>
            <summary>We present an empirical study of multi-agent systems in production software design.</summary>
            <published>2024-01-01T12:00:00Z</published>
        </entry>
    </feed>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = sample_atom_xml

    with patch("httpx.Client.get", return_value=mock_resp):
        records = search_arxiv("multi-agent software engineering", max_results=2)

    assert len(records) == 1
    assert records[0].title == "Multi-Agent Architectures for Software Engineering"
    assert records[0].url == "https://arxiv.org/abs/2401.00001v1"
    assert records[0].source_type == "Academic Paper / Preprint"
    assert records[0].publication_date == "2024-01-01"


def test_search_arxiv_handles_exceptions_gracefully():
    """Verifies that search_arxiv returns an empty list without raising exceptions when network fails."""
    with patch("httpx.Client.get", side_effect=TimeoutError("Connection to arXiv timed out")):
        records = search_arxiv("failing query", timeout=1.0)
    assert records == []


def test_specialized_ai_systems_plan():
    """Tests creation and validation of an AI systems specialized research plan."""
    plan = ResearchPlan(
        topic="Multi-Agent Systems vs Single-Agent Architectures in Production",
        research_objectives=[
            "Compare task decomposition and latency tradeoffs",
            "Evaluate tool calling coordination patterns like MCP",
        ],
        subquestions=[
            "What are the latency overheads of multi-agent coordination?",
            "How do orchestration frameworks manage error recovery and state?",
            "What failure modes arise with concurrent tool calling?",
        ],
        search_queries=[
            "multi-agent systems single-agent latency benchmarks",
            "Model Context Protocol tool calling architecture",
            "LangGraph state management trade-offs",
        ],
        expected_evidence=[
            "Empirical benchmark datasets",
            "Framework architectural specifications",
            "Production postmortems",
        ],
    )
    assert plan.topic.startswith("Multi-Agent Systems")
    assert len(plan.subquestions) == 3
    assert len(plan.search_queries) == 3
