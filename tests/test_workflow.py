"""
Integration and unit tests for the multi-agent workflow orchestration.
Verifies stage ordering, error recovery, API key validation, and citation auditing.
"""

from unittest.mock import patch
import pytest

from memory.repository import ResearchRepository
from models.schemas import (
    AnalysisResult,
    FindingItem,
    ReportReference,
    ResearchPlan,
    ResearchReport,
    SourceRecord,
)
from services.research_workflow import ResearchWorkflowService
from agents.writer import reconcile_and_audit_references


@pytest.fixture
def test_service(tmp_path):
    """Provides a ResearchWorkflowService backed by a clean temporary database."""
    db_file = tmp_path / "test_workflow.db"
    repo = ResearchRepository(db_path=str(db_file))
    return ResearchWorkflowService(repository=repo)


def test_missing_api_key_fails_cleanly(test_service):
    """Tests that missing GEMINI_API_KEY stops workflow immediately with clear error."""
    with patch("os.getenv", return_value=""):
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
            test_service.run_research(
                question="What is the future of quantum batteries?",
                skip_api_validation=False,
            )

    # Verify session is persisted as failed
    sessions = test_service.repository.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["status"] == "failed"


def test_reference_auditing_against_source_registry():
    """
    Verifies that reconcile_and_audit_references reconciles the report
    against real source records, filtering out imaginary URLs.
    """
    real_sources = [
        SourceRecord(
            title="Real Study 2026",
            url="https://verified.org/study-2026",
            snippet="Real empirical evidence.",
        ),
        SourceRecord(
            title="Real Benchmark",
            url="https://benchmarks.io/agent-eval",
            snippet="Agent benchmark scores.",
        ),
    ]

    # Report where LLM hallucinated an invalid URL
    hallucinated_report = ResearchReport(
        title="Agent Evaluation",
        executive_summary="Summary",
        research_question_and_objectives="Q & O",
        methodology="Method",
        key_findings="Findings",
        detailed_analysis="Analysis",
        conflicting_evidence_and_limitations="Limitations",
        conclusion="Conclusion",
        references=[
            ReportReference(
                index=1,
                title="Fake Study",
                url="https://hallucinated-fake-site.com/nonexistent",
            ),
            ReportReference(
                index=2,
                title="Real Study 2026",
                url="https://verified.org/study-2026",
            ),
        ],
    )

    audited = reconcile_and_audit_references(hallucinated_report, real_sources)

    # Every reference in audited report MUST be from real_sources
    ref_urls = [r.url for r in audited.references]
    assert "https://hallucinated-fake-site.com/nonexistent" not in ref_urls
    assert "https://verified.org/study-2026" in ref_urls


def test_complete_mocked_workflow_stage_ordering(test_service):
    """
    Executes an end-to-end multi-agent workflow using injected mocks.
    Verifies stage transitions: planning -> searching -> analyzing -> writing -> completed.
    """
    stages_visited = []

    def progress_tracker(stage, msg, step, total):
        stages_visited.append(stage)

    # Mock Planner
    def mock_planner(question, depth):
        return ResearchPlan(
            topic=question,
            research_objectives=["Understand trends", "Evaluate impact"],
            subquestions=[
                "What are the latest AI agent trends?",
                "How are developer workflows changing?",
            ],
            search_queries=[
                "AI agent trends 2026",
                "software engineering AI agents impact",
            ],
            expected_evidence=["Whitepapers", "Benchmark reports"],
        )

    # Mock Researcher
    def mock_researcher(plan, depth):
        return (
            [
                SourceRecord(
                    title="AI Agents in Software Engineering",
                    url="https://example.com/ai-agents",
                    snippet="Detailed study on agentic coding in 2026.",
                    relevant_query="AI agent trends 2026",
                )
            ],
            [],
        )

    # Mock Analyst
    def mock_analyst(plan, sources):
        return AnalysisResult(
            key_findings=[
                FindingItem(
                    theme="Automation",
                    statement="Agents handle 35% of repetitive pull requests.",
                    source_urls=[sources[0].url],
                    is_factual=True,
                )
            ],
            recurring_themes=["Developer augmentation"],
            conflicting_evidence=[],
            weak_sources=[],
            information_gaps=[],
            synthesis_notes="Strong initial validation.",
        )

    # Mock Writer
    def mock_writer(question, plan, sources, analysis):
        return ResearchReport(
            title="AI Agents in SE 2026",
            executive_summary="Summary",
            research_question_and_objectives="Q & O",
            methodology="Method",
            key_findings="Findings",
            detailed_analysis="Detailed",
            conflicting_evidence_and_limitations="Limitations",
            conclusion="Conclusion",
            references=[
                ReportReference(
                    index=1,
                    title=sources[0].title,
                    url=sources[0].url,
                )
            ],
            full_markdown="# AI Agents in SE 2026\n\nFull report content.",
        )

    session = test_service.run_research(
        question="How are AI agents transforming software engineering in 2026?",
        depth="Quick",
        progress_callback=progress_tracker,
        custom_planner_fn=mock_planner,
        custom_researcher_fn=mock_researcher,
        custom_analyst_fn=mock_analyst,
        custom_writer_fn=mock_writer,
        skip_api_validation=True,
    )

    assert session.status == "completed"
    assert session.plan is not None
    assert len(session.sources) == 1
    assert session.analysis is not None
    assert session.report is not None

    # Check stage order progression
    assert "Planning" in stages_visited
    assert "Searching" in stages_visited
    assert "Analyzing" in stages_visited
    assert "Writing" in stages_visited
    assert "Completed" in stages_visited

    # Verify persistent storage
    retrieved = test_service.repository.get_session(session.session_id)
    assert retrieved is not None
    assert retrieved.status == "completed"
    assert retrieved.report.title == "AI Agents in SE 2026"


def test_agent_failure_persists_error(test_service):
    """Tests that an exception during analysis updates session status to 'failed'."""
    def mock_planner(question, depth):
        return ResearchPlan(
            topic=question,
            research_objectives=["Objectives"],
            subquestions=["Subquestion 1", "Subquestion 2"],
            search_queries=["query 1", "query 2"],
            expected_evidence=["Evidence"],
        )

    def failing_researcher(plan, depth):
        raise ConnectionError("DNS failure reaching search service")

    with pytest.raises(ConnectionError, match="DNS failure"):
        test_service.run_research(
            question="Failing query?",
            depth="Quick",
            custom_planner_fn=mock_planner,
            custom_researcher_fn=failing_researcher,
            skip_api_validation=True,
        )

    sessions = test_service.repository.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["status"] == "failed"
