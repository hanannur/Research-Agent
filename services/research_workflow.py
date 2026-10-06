"""
Multi-Agent Workflow Orchestration Service for DeepResearch AI.
Coordinates the end-to-end execution pipeline across:
  Stage 1: Research Planning (Agent 1)
  Stage 2: Web Research Execution (Agent 2)
  Stage 3: Evidence Analysis (Agent 3)
  Stage 4: Report Writing & Citation Auditing (Agent 4)
  Stage 5: SQLite Memory Persistence
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from config import validate_api_key
from memory.repository import ResearchRepository
from models.schemas import (
    AnalysisResult,
    ResearchPlan,
    ResearchReport,
    ResearchSession,
    SourceRecord,
)
from agents.planner import plan_research
from agents.researcher import execute_web_research
from agents.analyst import analyze_evidence
from agents.writer import write_research_report

logger = logging.getLogger(__name__)

# Callback type signature: (stage_name, status_message, step_index, total_steps)
ProgressCallback = Callable[[str, str, int, int], None]


class ResearchWorkflowService:
    """Orchestrates the multi-agent research pipeline cleanly separated from UI."""

    TOTAL_STAGES = 5

    def __init__(self, repository: Optional[ResearchRepository] = None):
        self.repository = repository or ResearchRepository()

    def run_research(
        self,
        question: str,
        depth: str = "Standard",
        session_id: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
        # Injection hooks for unit testing / mocking
        custom_planner_fn: Optional[Callable] = None,
        custom_researcher_fn: Optional[Callable] = None,
        custom_analyst_fn: Optional[Callable] = None,
        custom_writer_fn: Optional[Callable] = None,
        skip_api_validation: bool = False,
    ) -> ResearchSession:
        """
        Executes the entire multi-agent research workflow.

        Args:
            question: User research question
            depth: "Quick", "Standard", or "Detailed"
            session_id: Optional explicit session ID
            progress_callback: Callback for real-time stage progress updates
            custom_*_fn: Optional mock functions for testing without external services
            skip_api_validation: Allow testing without checking real GEMINI_API_KEY
        """
        if not question or not question.strip():
            raise ValueError("Research question cannot be empty.")

        question = question.strip()
        sid = session_id or str(uuid.uuid4())

        session = ResearchSession(
            session_id=sid,
            created_at=datetime.now(timezone.utc).isoformat(),
            question=question,
            depth=depth,
            status="planning",
        )

        def report_progress(stage: str, msg: str, step: int):
            if progress_callback:
                progress_callback(stage, msg, step, self.TOTAL_STAGES)

        # 0. Validate API Key Prerequisites
        if not skip_api_validation and not custom_planner_fn:
            is_valid, err_msg = validate_api_key()
            if not is_valid:
                session.status = "failed"
                session.error_message = err_msg
                self.repository.save_session(session)
                raise ValueError(err_msg)

        try:
            # Save initial session in SQLite
            self.repository.save_session(session)

            # ==============================================================
            # STAGE 1: Research Planning (Agent 1)
            # ==============================================================
            report_progress("Planning", "Agent 1: Analyzing question and generating research plan...", 1)
            logger.info("[%s] Stage 1: Planning research for: %s", sid, question)

            if custom_planner_fn:
                plan: ResearchPlan = custom_planner_fn(question, depth)
            else:
                plan = plan_research(question=question, depth=depth)

            session.plan = plan
            session.status = "researching"
            self.repository.save_session(session)

            # ==============================================================
            # STAGE 2: Web Research Execution (Agent 2)
            # ==============================================================
            report_progress("Searching", f"Agent 2: Discovering and verifying sources across {len(plan.search_queries)} queries...", 2)
            logger.info("[%s] Stage 2: Web and preprint research with %d queries", sid, len(plan.search_queries))

            if custom_researcher_fn:
                sources, failed_queries = custom_researcher_fn(plan, depth)
            else:
                sources, failed_queries = execute_web_research(
                    plan=plan,
                    depth=depth,
                    progress_callback=lambda msg, cur, tot: report_progress("Searching", f"Agent 2: {msg}", 2),
                )

            session.sources = sources
            session.status = "analyzing"
            self.repository.save_session(session)

            # ==============================================================
            # STAGE 3: Evidence Analysis (Agent 3)
            # ==============================================================
            report_progress("Analyzing", f"Agent 3: Analyzing evidence across {len(sources)} sources...", 3)
            logger.info("[%s] Stage 3: Evidence analysis with %d sources", sid, len(sources))

            if custom_analyst_fn:
                analysis: AnalysisResult = custom_analyst_fn(plan, sources)
            else:
                analysis = analyze_evidence(plan=plan, sources=sources)

            session.analysis = analysis
            session.status = "writing"
            self.repository.save_session(session)

            # ==============================================================
            # STAGE 4: Report Writing & Reference Audit (Agent 4)
            # ==============================================================
            report_progress("Writing", "Agent 4: Compiling report and auditing source references...", 4)
            logger.info("[%s] Stage 4: Writing research report", sid)

            if custom_writer_fn:
                report: ResearchReport = custom_writer_fn(question, plan, sources, analysis)
            else:
                report = write_research_report(
                    question=question,
                    plan=plan,
                    sources=sources,
                    analysis=analysis,
                )

            session.report = report
            session.status = "completed"

            # ==============================================================
            # STAGE 5: SQLite Persistence
            # ==============================================================
            report_progress("Persisting", "Saving completed session to SQLite memory...", 5)
            self.repository.save_session(session)
            logger.info("[%s] Stage 5: Session completed and stored successfully.", sid)

            report_progress("Completed", "Research report ready!", 5)
            return session

        except Exception as exc:
            logger.error("[%s] Research workflow failed at status '%s': %s", sid, session.status, exc, exc_info=True)
            session.status = "failed"
            session.error_message = str(exc)
            try:
                self.repository.save_session(session)
            except Exception as save_err:
                logger.error("Failed to persist failed session: %s", save_err)
            raise
