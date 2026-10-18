"""
Repository layer providing CRUD and search operations over the SQLite memory store.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from config import DATABASE_PATH
from models.schemas import (
    AnalysisResult,
    ResearchPlan,
    ResearchReport,
    ResearchSession,
    SourceRecord,
)
from .database import get_db_connection, init_db

logger = logging.getLogger(__name__)


class ResearchRepository:
    """Manages persistent SQLite storage for DeepResearch AI sessions and user preferences."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def save_session(self, session: ResearchSession) -> None:
        """Persists or upserts a research session."""
        plan_json = session.plan.model_dump_json() if session.plan else None
        sources_json = (
            json.dumps([s.model_dump() for s in session.sources])
            if session.sources
            else None
        )
        analysis_json = (
            session.analysis.model_dump_json() if session.analysis else None
        )
        report_json = (
            session.report.model_dump_json() if session.report else None
        )
        full_markdown = session.report.full_markdown if session.report else ""

        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO research_sessions (
                    session_id, created_at, question, depth, status,
                    error_message, plan_json, sources_json, analysis_json,
                    report_json, full_markdown
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    status = excluded.status,
                    error_message = excluded.error_message,
                    plan_json = excluded.plan_json,
                    sources_json = excluded.sources_json,
                    analysis_json = excluded.analysis_json,
                    report_json = excluded.report_json,
                    full_markdown = excluded.full_markdown;
                """,
                (
                    session.session_id,
                    session.created_at,
                    session.question,
                    session.depth,
                    session.status,
                    session.error_message,
                    plan_json,
                    sources_json,
                    analysis_json,
                    report_json,
                    full_markdown,
                ),
            )
            conn.commit()

    def get_session(self, session_id: str) -> Optional[ResearchSession]:
        """Retrieves and deserializes a single research session by ID."""
        with get_db_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM research_sessions WHERE session_id = ?;",
                (session_id,),
            ).fetchone()

        if not row:
            return None

        plan = ResearchPlan.model_validate_json(row["plan_json"]) if row["plan_json"] else None

        sources = []
        if row["sources_json"]:
            try:
                sources_data = json.loads(row["sources_json"])
                sources = [SourceRecord.model_validate(s) for s in sources_data]
            except Exception as e:
                logger.warning("Error parsing sources for %s: %s", session_id, e)

        analysis = (
            AnalysisResult.model_validate_json(row["analysis_json"])
            if row["analysis_json"]
            else None
        )
        report = (
            ResearchReport.model_validate_json(row["report_json"])
            if row["report_json"]
            else None
        )

        return ResearchSession(
            session_id=row["session_id"],
            created_at=row["created_at"],
            question=row["question"],
            depth=row["depth"],
            status=row["status"],
            error_message=row["error_message"],
            plan=plan,
            sources=sources,
            analysis=analysis,
            report=report,
        )

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        """Returns metadata list of past research sessions for UI display."""
        with get_db_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT session_id, created_at, question, depth, status,
                       (CASE WHEN report_json IS NOT NULL THEN 1 ELSE 0 END) AS has_report
                FROM research_sessions
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (limit,),
            ).fetchall()

        return [dict(r) for r in rows]

    def search_past_sessions(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Transparent keyword search over historical research questions and reports.
        Helps users discover related prior research without claiming vector embeddings.
        """
        if not query or not query.strip():
            return []

        pattern = f"%{query.strip().lower()}%"
        with get_db_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT session_id, created_at, question, depth, status
                FROM research_sessions
                WHERE lower(question) LIKE ?
                   OR lower(full_markdown) LIKE ?
                   OR lower(plan_json) LIKE ?
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (pattern, pattern, pattern, limit),
            ).fetchall()

        return [dict(r) for r in rows]

    def delete_session(self, session_id: str) -> bool:
        """Deletes a specific session."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM research_sessions WHERE session_id = ?;",
                (session_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_history(self) -> int:
        """Deletes all session records, preserving user preferences."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM research_sessions;")
            conn.commit()
            return cursor.rowcount

    # User Preferences (separated from research history)
    def get_preference(self, key: str, default: str = "") -> str:
        """Retrieves a persistent user preference string."""
        with get_db_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT pref_value FROM user_preferences WHERE pref_key = ?;",
                (key,),
            ).fetchone()
        return row["pref_value"] if row else default

    def set_preference(self, key: str, value: str) -> None:
        """Sets a persistent user preference string."""
        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_preferences (pref_key, pref_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(pref_key) DO UPDATE SET
                    pref_value = excluded.pref_value,
                    updated_at = excluded.updated_at;
                """,
                (key, value, now),
            )
            conn.commit()
