"""
DeepResearch AI — Multi-Agent Research Assistant
Specialization: AI Systems & Software Engineering Research
Interactive Streamlit Dashboard.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import streamlit as st

# Ensure repository root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DEPTH_CONFIG, GEMINI_MODEL, validate_api_key
from memory.repository import ResearchRepository
from models.schemas import ResearchSession, SourceRecord
from services.research_workflow import ResearchWorkflowService

# Page Configuration
st.set_page_config(
    page_title="DeepResearch AI — AI Systems & Software Engineering Research",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Editorial Styling: Paper-like, restrained, scholarly typography
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #1a202c;
    }

    /* Elegant Editorial Headings */
    h1, h2, h3, .editorial-heading {
        font-family: 'Newsreader', Georgia, serif;
        font-weight: 600;
        letter-spacing: -0.01em;
        color: #0f172a;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.88rem;
    }

    /* Main Container Spacing */
    .main .block-container {
        padding-top: 1.75rem;
        padding-bottom: 3.5rem;
        max-width: 1140px;
    }

    /* Scholarly Header */
    .editorial-header {
        background-color: #fcfbf9;
        border: 1px solid #e7e4dc;
        border-radius: 6px;
        padding: 1.25rem 1.75rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }
    .editorial-title {
        font-family: 'Newsreader', Georgia, serif;
        font-size: 2.15rem;
        font-weight: 600;
        color: #0f172a;
        margin: 0;
        line-height: 1.2;
    }
    .editorial-tagline {
        color: #525d6d;
        font-size: 1.0rem;
        margin-top: 0.35rem;
        margin-bottom: 0.5rem;
        font-style: italic;
    }
    .specialization-badge {
        display: inline-block;
        font-size: 0.73rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        background-color: #f1ede4;
        color: #854d0e;
        border: 1px solid #dfd7c8;
    }

    /* Example questions pill buttons */
    .sample-chip {
        font-size: 0.82rem;
        padding: 0.35rem 0.65rem;
        border-radius: 4px;
        background-color: #f8f7f4;
        border: 1px solid #e2ded5;
        color: #334155;
        display: inline-block;
        margin-bottom: 0.4rem;
    }

    /* Research Progress Card */
    .stage-card {
        background-color: #ffffff;
        border: 1px solid #e6e3da;
        border-radius: 6px;
        padding: 0.85rem 1.15rem;
        margin-bottom: 0.75rem;
    }

    .status-badge {
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 3px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .status-completed { background-color: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
    .status-running { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .status-pending { background-color: #f8fafc; color: #64748b; border: 1px solid #e2e8f0; }
    .status-failed { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }

    /* Source Cards */
    .source-card {
        background-color: #ffffff;
        border: 1px solid #e6e3da;
        border-left: 3px solid #b45309;
        border-radius: 0 4px 4px 0;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.85rem;
    }
    .source-card-academic { border-left-color: #0284c7; }
    .source-card-docs { border-left-color: #059669; }
    .source-card-blog { border-left-color: #b45309; }
    .source-card-web { border-left-color: #64748b; }

    .source-type-pill {
        display: inline-block;
        font-size: 0.70rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 0.15rem 0.45rem;
        border-radius: 3px;
        margin-bottom: 0.35rem;
    }
    .pill-academic { background-color: #f0f9ff; color: #0369a1; border: 1px solid #bae6fd; }
    .pill-docs { background-color: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
    .pill-blog { background-color: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
    .pill-web { background-color: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }

    .source-card-title {
        font-weight: 600;
        font-size: 0.95rem;
        color: #0f172a;
    }
    .source-card-url {
        font-size: 0.80rem;
        color: #2563eb;
        text-decoration: none;
        word-break: break-all;
    }
    .source-card-url:hover { text-decoration: underline; }
    .source-card-snippet {
        font-size: 0.85rem;
        color: #475569;
        margin-top: 0.35rem;
        line-height: 1.45;
    }

    /* Analytical Findings Box */
    .finding-box {
        background-color: #ffffff;
        border: 1px solid #e6e3da;
        border-radius: 5px;
        padding: 0.85rem 1.15rem;
        margin-bottom: 0.75rem;
    }
    .finding-fact {
        border-left: 3px solid #059669;
    }
    .finding-interpretation {
        border-left: 3px solid #d97706;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_service() -> ResearchWorkflowService:
    """Initializes and caches the workflow service and database repository."""
    repo = ResearchRepository()
    return ResearchWorkflowService(repository=repo)


service = get_service()

# Initialize Session State
if "current_session" not in st.session_state:
    st.session_state.current_session = None
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "workflow_stage" not in st.session_state:
    st.session_state.workflow_stage = "Idle"
if "stage_logs" not in st.session_state:
    st.session_state.stage_logs = []
if "query_input" not in st.session_state:
    st.session_state.query_input = ""
if "confirm_clear" not in st.session_state:
    st.session_state.confirm_clear = False


# ==============================================================================
# SIDEBAR: Research History, Search, and Configuration
# ==============================================================================
with st.sidebar:
    st.markdown("### Research Archive")
    st.caption("SQLite persistent memory of prior investigations.")

    # Search past sessions
    search_keyword = st.text_input(
        "Search Archive",
        placeholder="Search past research (e.g., RAG, MCP, LangGraph)...",
        label_visibility="collapsed",
    )

    if search_keyword.strip():
        past_sessions = service.repository.search_past_sessions(search_keyword.strip())
        st.caption(f"Found {len(past_sessions)} matching record(s):")
    else:
        past_sessions = service.repository.list_sessions(limit=30)

    if not past_sessions:
        st.info("No research sessions found in the archive.")
    else:
        for sess in past_sessions:
            sid = sess["session_id"]
            q_short = sess["question"][:42] + ("..." if len(sess["question"]) > 42 else "")
            dt_str = sess["created_at"][:10] if "created_at" in sess else ""
            status_symbol = "✓" if sess["status"] == "completed" else ("✗" if sess["status"] == "failed" else "…")

            with st.expander(f"{status_symbol} {q_short} ({dt_str})"):
                st.caption(f"**Session**: `{sid[:8]}...` | **Depth**: {sess.get('depth', 'Standard')}")
                st.caption(f"**Status**: `{sess['status']}`")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Open Report", key=f"view_{sid}", use_container_width=True):
                        loaded = service.repository.get_session(sid)
                        if loaded:
                            st.session_state.current_session = loaded
                            st.rerun()

                with col_btn2:
                    if st.button("Reuse Query", key=f"reuse_{sid}", use_container_width=True):
                        st.session_state.query_input = sess["question"]
                        st.rerun()

    st.markdown("---")

    # Clear History Action with Confirmation
    st.markdown("### Manage Archive")
    if not st.session_state.confirm_clear:
        if st.button("Clear Research History", type="secondary", use_container_width=True):
            st.session_state.confirm_clear = True
            st.rerun()
    else:
        st.warning("Confirm deleting all past research sessions?")
        c_yes, c_no = st.columns(2)
        with c_yes:
            if st.button("Yes, Clear", type="primary", use_container_width=True):
                service.repository.clear_all_history()
                st.session_state.current_session = None
                st.session_state.confirm_clear = False
                st.success("Research archive cleared.")
                st.rerun()
        with c_no:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_clear = False
                st.rerun()

    st.markdown("---")
    st.markdown("### System & Credentials")
    api_valid, api_msg = validate_api_key()
    if api_valid:
        st.success("Gemini API key is configured.")
    else:
        st.error(api_msg)
        api_override = st.text_input("Enter Gemini API Key", type="password")
        if st.button("Save API Key"):
            if api_override.strip():
                os.environ["GEMINI_API_KEY"] = api_override.strip()
                st.success("API key registered for the active session.")
                st.rerun()

    st.caption("Search Engine: DuckDuckGo + arXiv public API (No paid search key required).")


# ==============================================================================
# MAIN WORKSPACE
# ==============================================================================

# Scholarly Header
st.markdown(
    """
    <div class="editorial-header">
        <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 0.5rem;">
            <h1 class="editorial-title">DeepResearch AI</h1>
            <span class="specialization-badge">AI Systems & Software Engineering Research</span>
        </div>
        <div class="editorial-tagline">From complex questions to evidence-based insights.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Curated AI Systems & Software Engineering Research Examples
example_questions = [
    "How do multi-agent systems differ from single-agent architectures?",
    "Compare RAG and long-context approaches for production AI systems.",
    "How does agent memory improve long-running AI workflows?",
    "What are the trade-offs between LangGraph and other agent orchestration frameworks?",
    "What are the main security risks when AI agents use external tools?",
]

st.markdown("<p style='font-size: 0.88rem; color: #475569; margin-bottom: 0.35rem;'>Select an example research inquiry:</p>", unsafe_allow_html=True)

# Render sample question pills in columns
sample_cols = st.columns(len(example_questions))
for idx, q_text in enumerate(example_questions):
    with sample_cols[idx]:
        short_label = f"Topic {idx + 1}"
        if idx == 0: short_label = "Multi-Agent vs Single"
        elif idx == 1: short_label = "RAG vs Long-Context"
        elif idx == 2: short_label = "Agent Memory"
        elif idx == 3: short_label = "Orchestration"
        elif idx == 4: short_label = "Tool Security"

        if st.button(short_label, help=q_text, use_container_width=True):
            st.session_state.query_input = q_text
            st.rerun()

# Research Input Form
with st.container():
    col_input, col_depth = st.columns([3, 1])

    with col_input:
        research_query = st.text_area(
            "Research Inquiry",
            value=st.session_state.query_input,
            placeholder="Formulate a complex AI systems or software engineering question (e.g., 'How do multi-agent systems differ from single-agent architectures in production?')...",
            height=95,
            label_visibility="collapsed",
        )

    with col_depth:
        depth_option = st.selectbox(
            "Research Depth",
            options=["Quick", "Standard", "Detailed"],
            index=1,
            help=(
                "Quick: 2 queries (~30s, 3-6 verified sources)\n"
                "Standard: 3-4 queries (~60s, 8-12 verified sources)\n"
                "Detailed: 5-6 queries (~120s, 15-25 verified sources & academic preprints)"
            ),
        )
        depth_info = DEPTH_CONFIG[depth_option]["description"]
        st.caption(f"Scope: {depth_info}")

    start_col, info_col = st.columns([1, 4])
    with start_col:
        start_btn = st.button(
            "Start Research",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.is_running,
        )
    with info_col:
        st.caption("Runs an orchestrated 4-stage pipeline: Planning → Web & Preprint Discovery → Evidence Analysis → Audited Synthesis.")


# ==============================================================================
# WORKFLOW EXECUTION
# ==============================================================================
if start_btn:
    if not research_query.strip():
        st.warning("Please enter a research question to begin.")
    else:
        st.session_state.is_running = True
        st.session_state.stage_logs = []
        progress_bar = st.progress(0, text="Initializing DeepResearch AI multi-agent pipeline...")
        status_box = st.status("Orchestrating Research Workflow...", expanded=True)

        def on_workflow_progress(stage: str, msg: str, step: int, total: int):
            st.session_state.workflow_stage = stage
            pct = int((step / total) * 100)
            progress_bar.progress(pct, text=f"Stage {step}/{total}: {msg}")
            status_box.write(f"**[{stage}]** {msg}")
            st.session_state.stage_logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] [{stage}] {msg}"
            )

        try:
            completed_session = service.run_research(
                question=research_query.strip(),
                depth=depth_option,
                progress_callback=on_workflow_progress,
            )
            st.session_state.current_session = completed_session
            st.session_state.is_running = False
            status_box.update(
                label="Research Investigation Completed Successfully",
                state="complete",
                expanded=False,
            )
            st.toast("Evidence-based research report synthesized!", icon="📑")
            st.rerun()

        except Exception as exc:
            st.session_state.is_running = False
            status_box.update(
                label=f"Workflow Interrupted: {exc}", state="error", expanded=True
            )
            st.error(f"Error during research workflow: {exc}")


# ==============================================================================
# REPORT AND EVIDENCE WORKSPACE
# ==============================================================================
active_session: ResearchSession = st.session_state.current_session

if active_session:
    st.markdown("---")

    # Header with metadata and report export actions
    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        st.markdown(f"### Research Report: *{active_session.question}*")
        st.caption(
            f"Session: `{active_session.session_id[:8]}` | "
            f"Depth: `{active_session.depth}` | "
            f"Status: `{active_session.status}` | "
            f"Sources: `{len(active_session.sources)} verified`"
        )
    with h_col2:
        if active_session.report and active_session.report.full_markdown:
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                st.download_button(
                    label="Download .MD",
                    data=active_session.report.full_markdown,
                    file_name=f"DeepResearch_{active_session.session_id[:8]}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with dl_col2:
                st.download_button(
                    label="Download .TXT",
                    data=active_session.report.full_markdown,
                    file_name=f"DeepResearch_{active_session.session_id[:8]}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

    # 4 Main Analytical Tabs
    tab_report, tab_sources, tab_analysis, tab_plan = st.tabs(
        [
            "Editorial Report",
            f"Evidence Registry ({len(active_session.sources)})",
            "Evidence Analysis & Factuality",
            "Research Plan & Scope",
        ]
    )

    # TAB 1: Editorial Research Report
    with tab_report:
        if active_session.report and active_session.report.full_markdown:
            st.markdown(active_session.report.full_markdown)
        elif active_session.status == "failed":
            st.error(f"Research pipeline halted: {active_session.error_message}")
        else:
            st.info("Report synthesis pending.")

    # TAB 2: Categorized Evidence Registry
    with tab_sources:
        if not active_session.sources:
            st.info("No sources retrieved yet.")
        else:
            academic_sources = [s for s in active_session.sources if s.source_type == "Academic Paper / Preprint"]
            docs_sources = [s for s in active_session.sources if s.source_type == "Official Documentation"]
            blog_sources = [s for s in active_session.sources if s.source_type == "Engineering Blog / Technical Article"]
            web_sources = [s for s in active_session.sources if s.source_type not in ("Academic Paper / Preprint", "Official Documentation", "Engineering Blog / Technical Article")]

            st.caption(
                f"Retrieved and deduplicated {len(active_session.sources)} verified sources across DuckDuckGo and academic preprints."
            )

            def render_source_card(src: SourceRecord, index: int, pill_class: str, card_class: str):
                pub_info = f" | Published: {src.publication_date}" if src.publication_date else ""
                st.markdown(
                    f"""
                    <div class="source-card {card_class}">
                        <span class="source-type-pill {pill_class}">{src.source_type}</span>
                        <div class="source-card-title">[{index}] {src.title}</div>
                        <a href="{src.url}" target="_blank" class="source-card-url">{src.url}</a>
                        <div class="source-card-snippet">{src.snippet}</div>
                        <div style="font-size: 0.74rem; color: #64748b; margin-top: 0.35rem;">
                            Query: <i>"{src.relevant_query or 'General'}"</i>{pub_info}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Sub-sections for categorized evidence
            if academic_sources:
                st.markdown(f"#### Academic Papers & Preprints ({len(academic_sources)})")
                for i, s in enumerate(academic_sources, 1):
                    render_source_card(s, i, "pill-academic", "source-card-academic")

            if docs_sources:
                st.markdown(f"#### Official Documentation & Specifications ({len(docs_sources)})")
                for i, s in enumerate(docs_sources, 1):
                    render_source_card(s, i, "pill-docs", "source-card-docs")

            if blog_sources:
                st.markdown(f"#### Engineering Articles & Technical Blogs ({len(blog_sources)})")
                for i, s in enumerate(blog_sources, 1):
                    render_source_card(s, i, "pill-blog", "source-card-blog")

            if web_sources:
                st.markdown(f"#### Other Web Sources ({len(web_sources)})")
                for i, s in enumerate(web_sources, 1):
                    render_source_card(s, i, "pill-web", "source-card-web")

    # TAB 3: Evidence Analysis & Factuality
    with tab_analysis:
        if not active_session.analysis:
            st.info("Evidence analysis pending.")
        else:
            ana = active_session.analysis

            st.markdown("#### Key Empirical Findings")
            for f in ana.key_findings:
                finding_class = "finding-fact" if f.is_factual else "finding-interpretation"
                tag_label = "FACT" if f.is_factual else "INTERPRETATION"
                tag_color = "#047857" if f.is_factual else "#b45309"
                tag_bg = "#ecfdf5" if f.is_factual else "#fffbeb"

                urls_display = ""
                if f.source_urls:
                    urls_links = [f"<a href='{u}' target='_blank' style='font-size: 0.78rem; color: #2563eb;'>{u}</a>" for u in f.source_urls]
                    urls_display = f"<div style='margin-top: 0.35rem; font-size: 0.78rem; color: #64748b;'>Supporting Evidence: {', '.join(urls_links)}</div>"

                st.markdown(
                    f"""
                    <div class="finding-box {finding_class}">
                        <span style="font-size: 0.70rem; font-weight: 700; padding: 0.15rem 0.45rem; border-radius: 3px; background-color: {tag_bg}; color: {tag_color}; text-transform: uppercase;">{tag_label}</span>
                        <strong style="margin-left: 0.4rem; color: #0f172a;">{f.theme}</strong>
                        <span style="font-size: 0.80rem; color: #64748b;">(Confidence: {f.confidence})</span>
                        <div style="margin-top: 0.4rem; color: #334155; line-height: 1.5;">{f.statement}</div>
                        {urls_display}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Two columns for Synthesis, Limitations & Disagreements
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### Recurring Themes")
                if ana.recurring_themes:
                    for th in ana.recurring_themes:
                        st.markdown(f"- {th}")
                else:
                    st.caption("No recurring patterns noted.")

                st.markdown("#### Information Gaps")
                if ana.information_gaps:
                    for gap in ana.information_gaps:
                        st.markdown(f"- {gap}")
                else:
                    st.caption("No significant evidence gaps identified.")

            with col_b:
                st.markdown("#### Conflicting Evidence & Trade-offs")
                if ana.conflicting_evidence:
                    for conf in ana.conflicting_evidence:
                        st.markdown(f"- {conf}")
                else:
                    st.caption("No significant direct contradictions identified.")

                st.markdown("#### Snippet Caveats & Weak Sources")
                if ana.weak_sources:
                    for weak in ana.weak_sources:
                        st.markdown(f"- {weak}")
                else:
                    st.caption("All retrieved snippets met baseline technical relevance.")

            st.markdown("#### Synthesis Assessment")
            st.info(ana.synthesis_notes)

    # TAB 4: Research Plan & Scope
    with tab_plan:
        if not active_session.plan:
            st.info("Research plan pending.")
        else:
            plan = active_session.plan
            st.markdown(f"**Research Topic**: `{plan.topic}`")

            st.markdown("#### Objectives")
            for obj in plan.research_objectives:
                st.markdown(f"- {obj}")

            st.markdown("#### Focused Subquestions")
            for subq in plan.subquestions:
                st.markdown(f"- {subq}")

            st.markdown("#### Formulated Search Queries")
            for q in plan.search_queries:
                st.code(q, language="text")

            st.markdown("#### Expected Evidence Types")
            for ev in plan.expected_evidence:
                st.markdown(f"- {ev}")
