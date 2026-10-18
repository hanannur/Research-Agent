"""
Unit tests for SQLite persistent memory and repository.
Verifies session storage, deserialization, keyword search, and clearing history.
"""

import pytest

from memory.repository import ResearchRepository
from models.schemas import (
    AnalysisResult,
    FindingItem,
    ReportReference,
    ResearchPlan,
    ResearchReport,
    ResearchSession,
    SourceRecord,
)


@pytest.fixture
def temp_repo(tmp_path):
    """Provides an isolated ResearchRepository backed by a temporary SQLite file."""
    db_file = tmp_path / "test_research.db"
    return ResearchRepository(db_path=str(db_file))


def test_save_and_get_session(temp_repo):
    """Tests saving a complete research session and retrieving it intact."""
    plan = ResearchPlan(
        topic="Quantum Computing Cryptography",
        research_objectives=["Review post-quantum standards"],
        subquestions=[
            "What are NIST post-quantum standards?",
            "How do organizations migrate to quantum-resistant encryption?",
        ],
        search_queries=[
            "NIST post-quantum standards 2026",
            "quantum resistant encryption migration",
        ],
        expected_evidence=["NIST publication", "Industry transition guidelines"],
    )
    sources = [
        SourceRecord(
            title="NIST Standards",
            url="https://csrc.nist.gov/pqc",
            snippet="PQC standards finalized.",
            relevant_query="NIST post-quantum standards",
        )
    ]
    analysis = AnalysisResult(
        key_findings=[
            FindingItem(
                theme="Standards",
                statement="NIST published initial PQC standards.",
                source_urls=["https://csrc.nist.gov/pqc"],
                is_factual=True,
            )
        ],
        recurring_themes=["Lattice-based cryptography"],
        conflicting_evidence=[],
        weak_sources=[],
        information_gaps=[],
        synthesis_notes="Solid consensus on standards.",
    )
    report = ResearchReport(
        title="Post-Quantum Cryptography Report",
        executive_summary="Summary of PQC landscape.",
        research_question_and_objectives="Question & Objectives",
        methodology="Multi-agent search",
        key_findings="Key findings text",
        detailed_analysis="Analysis text",
        conflicting_evidence_and_limitations="Limitations text",
        conclusion="Conclusion text",
        references=[
            ReportReference(
                index=1,
                title="NIST Standards",
                url="https://csrc.nist.gov/pqc",
            )
        ],
        full_markdown="# Post-Quantum Cryptography Report",
    )

    session = ResearchSession(
        session_id="session-test-123",
        question="How is post-quantum cryptography progressing?",
        depth="Standard",
        status="completed",
        plan=plan,
        sources=sources,
        analysis=analysis,
        report=report,
    )

    temp_repo.save_session(session)

    retrieved = temp_repo.get_session("session-test-123")
    assert retrieved is not None
    assert retrieved.session_id == "session-test-123"
    assert retrieved.question == "How is post-quantum cryptography progressing?"
    assert retrieved.status == "completed"
    assert retrieved.plan is not None
    assert retrieved.plan.topic == "Quantum Computing Cryptography"
    assert len(retrieved.sources) == 1
    assert retrieved.sources[0].url == "https://csrc.nist.gov/pqc"
    assert retrieved.analysis is not None
    assert len(retrieved.analysis.key_findings) == 1
    assert retrieved.report is not None
    assert retrieved.report.title == "Post-Quantum Cryptography Report"


def test_list_and_search_past_sessions(temp_repo):
    """Tests session listing and transparent keyword search."""
    session1 = ResearchSession(
        session_id="s1",
        question="What is the future of electric aviation?",
        depth="Quick",
        status="completed",
    )
    session2 = ResearchSession(
        session_id="s2",
        question="How does generative AI impact cybersecurity?",
        depth="Detailed",
        status="completed",
    )
    temp_repo.save_session(session1)
    temp_repo.save_session(session2)

    sessions_list = temp_repo.list_sessions()
    assert len(sessions_list) == 2

    # Search by keyword "aviation"
    aviation_results = temp_repo.search_past_sessions("aviation")
    assert len(aviation_results) == 1
    assert aviation_results[0]["session_id"] == "s1"

    # Search by keyword "cybersecurity"
    cyber_results = temp_repo.search_past_sessions("cybersecurity")
    assert len(cyber_results) == 1
    assert cyber_results[0]["session_id"] == "s2"


def test_clear_all_history_preserves_preferences(temp_repo):
    """Tests that clear_all_history wipes sessions but preserves user preferences."""
    session = ResearchSession(
        session_id="to-delete",
        question="Temporary query?",
        depth="Quick",
        status="completed",
    )
    temp_repo.save_session(session)
    temp_repo.set_preference("default_depth", "Detailed")

    deleted_count = temp_repo.clear_all_history()
    assert deleted_count == 1
    assert len(temp_repo.list_sessions()) == 0

    # User preferences MUST remain intact
    assert temp_repo.get_preference("default_depth") == "Detailed"
