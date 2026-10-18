"""
Unit tests for Pydantic data schemas.
Verifies structure, validation constraints, and serialization.
"""

import pytest
from pydantic import ValidationError

from models.schemas import (
    AnalysisResult,
    FindingItem,
    ReportReference,
    ResearchPlan,
    ResearchReport,
    ResearchSession,
    SourceRecord,
)


def test_research_plan_valid():
    """Tests valid ResearchPlan creation."""
    plan = ResearchPlan(
        topic="AI in Healthcare",
        research_objectives=["Assess clinical adoption", "Identify safety risks"],
        subquestions=[
            "What FDA approvals exist for AI diagnostic tools?",
            "What are physician adoption rates in 2026?",
        ],
        search_queries=[
            "FDA AI medical device approvals 2026",
            "clinical AI adoption rates hospital",
        ],
        expected_evidence=["Peer-reviewed medical trials", "FDA database listings"],
    )
    assert plan.topic == "AI in Healthcare"
    assert len(plan.subquestions) == 2
    assert len(plan.search_queries) == 2


def test_research_plan_invalid():
    """Tests validation error when subquestions or objectives are missing."""
    with pytest.raises(ValidationError):
        ResearchPlan(
            topic="Empty Plan",
            research_objectives=[],  # min_length=1
            subquestions=["Single question only"],  # min_length=2
            search_queries=[],
            expected_evidence=[],
        )


def test_source_record_validation():
    """Tests valid and invalid SourceRecord URL formatting."""
    valid_src = SourceRecord(
        title="Valid Site",
        url="https://example.com/research",
        snippet="A snippet about research.",
        relevant_query="research query",
    )
    assert valid_src.url == "https://example.com/research"

    # Invalid URL scheme
    with pytest.raises(ValidationError):
        SourceRecord(
            title="Bad Scheme",
            url="ftp://example.com/file",
            snippet="Snippet",
        )


def test_finding_item_factuality():
    """Tests FindingItem factuality distinction."""
    fact_finding = FindingItem(
        theme="Adoption",
        statement="72% of surveyed hospitals deployed clinical AI tools.",
        source_urls=["https://example.com/survey"],
        is_factual=True,
    )
    assert fact_finding.is_factual is True

    opinion_finding = FindingItem(
        theme="Analysis",
        statement="Clinical adoption will likely accelerate due to regulatory clarity.",
        source_urls=[],
        is_factual=False,
    )
    assert opinion_finding.is_factual is False


def test_report_markdown_assembly():
    """Tests ResearchReport Markdown rendering."""
    report = ResearchReport(
        title="AI in Software Engineering 2026",
        executive_summary="Executive briefing on developer productivity.",
        research_question_and_objectives="How are agents transforming SE?",
        methodology="Multi-agent search with DuckDuckGo.",
        key_findings="Agents write 40% of boilerplate code.",
        detailed_analysis="Detailed thematic breakdown.",
        conflicting_evidence_and_limitations="Benchmarks vary between synthetic and real-world codebases.",
        conclusion="Agents enhance rather than replace senior engineers.",
        references=[
            ReportReference(
                index=1,
                title="State of Code 2026",
                url="https://example.com/report2026",
                snippet="Survey of 5,000 engineers.",
            )
        ],
    )

    markdown = report.assemble_markdown()
    assert "# AI in Software Engineering 2026" in markdown
    assert "## Executive Summary" in markdown
    assert "1. [State of Code 2026](https://example.com/report2026)" in markdown
    assert "Survey of 5,000 engineers." in markdown
