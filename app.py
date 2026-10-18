"""
DeepResearch AI — Multi-Agent Research Assistant
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
from models.schemas import ResearchSession
from services.research_workflow import ResearchWorkflowService

# Page Configuration
st.set_page_config(
    page_title="DeepResearch AI — Multi-Agent Assistant",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    /* Sleek typography & layout */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Main Container Padding */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Hero Header */
    .hero-container {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.0rem;
        margin-bottom: 0;
    }

    /* Cards */
    .card-box {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(148, 163, 184, 0.12);
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
    }

    /* Stage Chip */
    .stage-chip {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-right: 0.5rem;
    }
    .chip-completed { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.3); }
    .chip-running { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.3); }
    .chip-pending { background: rgba(148, 163, 184, 0.1); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.2); }
    .chip-failed { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.3); }

    /* Source Item */
    .source-item {
        background: rgba(15, 23, 42, 0.5);
        border-left: 3px solid #3b82f6;
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
        border-radius: 0 8px 8px 0;
    }
    .source-title {
        font-weight: 600;
        font-size: 0.95rem;
        color: #e2e8f0;
    }
    .source-snippet {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-top: 0.25rem;
    }
    .source-link {
        font-size: 0.78rem;
        color: #60a5fa;
        text-decoration: none;
        word-break: break-all;
    }
    .source-link:hover { text-decoration: underline; }
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
# SIDEBAR: Research History, Memory Retrieval, and Configuration
# ==============================================================================
with st.sidebar:
    st.markdown("### 🧠 Persistent Memory")
    st.caption("SQLite local store of research runs and sources.")

    # Search past sessions
    search_keyword = st.text_input(
        "Search History",
        placeholder="Keyword (e.g. quantum, agents)...",
        label_visibility="collapsed",
    )

    if search_keyword.strip():
        past_sessions = service.repository.search_past_sessions(search_keyword.strip())
        st.caption(f"Found {len(past_sessions)} matching sessions:")
    else:
        past_sessions = service.repository.list_sessions(limit=25)

    if not past_sessions:
        st.info("No past research sessions found.")
    else:
        for sess in past_sessions:
            sid = sess["session_id"]
            q_short = sess["question"][:42] + ("..." if len(sess["question"]) > 42 else "")
            dt_str = sess["created_at"][:10]
            status_icon = "✅" if sess["status"] == "completed" else ("❌" if sess["status"] == "failed" else "⏳")

            with st.expander(f"{status_icon} {q_short} ({dt_str})"):
                st.caption(f"**ID**: `{sid[:8]}...` | **Depth**: {sess.get('depth', 'Standard')}")
                st.caption(f"**Status**: `{sess['status']}`")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("View Report", key=f"view_{sid}"):
                        loaded = service.repository.get_session(sid)
                        if loaded:
                            st.session_state.current_session = loaded
                            st.rerun()

                with col_btn2:
                    if st.button("Reuse Query", key=f"reuse_{sid}"):
                        st.session_state.query_input = sess["question"]
                        st.rerun()

    st.markdown("---")

    # Clear History Action with Confirmation
    st.markdown("### 🗑️ Manage History")
    if not st.session_state.confirm_clear:
        if st.button("Clear Research History", type="secondary", use_container_width=True):
            st.session_state.confirm_clear = True
            st.rerun()
    else:
        st.warning("Are you sure? This deletes all past research sessions.")
        c_yes, c_no = st.columns(2)
        with c_yes:
            if st.button("Yes, Clear", type="primary", use_container_width=True):
                service.repository.clear_all_history()
                st.session_state.current_session = None
                st.session_state.confirm_clear = False
                st.success("History cleared!")
                st.rerun()
        with c_no:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_clear = False
                st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ System Config")
    api_valid, api_msg = validate_api_key()
    if api_valid:
        st.success(f"Gemini API: Connected\nModel: `{GEMINI_MODEL}`", icon="🟢")
    else:
        st.error(api_msg, icon="🔴")
        api_override = st.text_input("Enter Gemini API Key", type="password")
        if st.button("Save API Key"):
            if api_override.strip():
                os.environ["GEMINI_API_KEY"] = api_override.strip()
                st.success("API Key updated in runtime environment!")
                st.rerun()

    st.caption("DuckDuckGo: Active (No API Key Required)")


# ==============================================================================
# MAIN DASHBOARD AREA
# ==============================================================================

# Hero Header
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">DeepResearch AI</div>
        <p class="hero-subtitle">
            Autonomous multi-agent research assistant. Powered by <b>PydanticAI</b>, <b>Google Gemini</b>, 
            <b>DuckDuckGo Live Search</b>, and <b>SQLite Persistent Memory</b>.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sample Questions Quick Selector
sample_questions = [
    "How are AI agents changing software engineering in 2026?",
    "What are the major breakthrough developments in quantum computing in 2026?",
    "What is the current state and outlook for commercial nuclear fusion power?",
    "How is autonomous robotic surgery regulated by global health authorities?",
]

with st.expander("💡 Click to pick an example research question", expanded=False):
    s_cols = st.columns(len(sample_questions))
    for idx, sq in enumerate(sample_questions):
        with s_cols[idx]:
            if st.button(f"Example {idx + 1}", help=sq, use_container_width=True):
                st.session_state.query_input = sq
                st.rerun()

# Research Input Form
with st.container():
    col_input, col_depth = st.columns([3, 1])

    with col_input:
        research_query = st.text_area(
            "Research Question",
            value=st.session_state.query_input,
            placeholder="Enter a complex research question (e.g. 'How are AI agents changing software engineering in 2026?')...",
            height=90,
            label_visibility="collapsed",
        )

    with col_depth:
        depth_option = st.selectbox(
            "Research Depth",
            options=["Quick", "Standard", "Detailed"],
            index=1,
            help=(
                "Quick: 2 queries (~30s, 3-6 sources)\n"
                "Standard: 3-4 queries (~60s, 8-12 sources)\n"
                "Detailed: 5-6 queries (~120s, 15-25 sources)"
            ),
        )
        depth_info = DEPTH_CONFIG[depth_option]["description"]
        st.caption(f"⚡ {depth_info}")

    start_col, stop_col, _ = st.columns([1, 1, 3])
    with start_col:
        start_btn = st.button(
            "🚀 Start Research",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.is_running,
        )

# ==============================================================================
# WORKFLOW EXECUTION
# ==============================================================================
if start_btn:
    if not research_query.strip():
        st.warning("Please enter a research question first.")
    else:
        st.session_state.is_running = True
        st.session_state.stage_logs = []
        progress_bar = st.progress(0, text="Initializing DeepResearch AI...")
        status_box = st.status("Executing Research Workflow...", expanded=True)

        def on_workflow_progress(stage: str, msg: str, step: int, total: int):
            st.session_state.workflow_stage = stage
            pct = int((step / total) * 100)
            progress_bar.progress(pct, text=f"Stage {step}/{total}: {msg}")
            status_box.write(f"**[{stage}]** {msg}")
            st.session_state.stage_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [{stage}] {msg}")

        try:
            completed_session = service.run_research(
                question=research_query.strip(),
                depth=depth_option,
                progress_callback=on_workflow_progress,
            )
            st.session_state.current_session = completed_session
            st.session_state.is_running = False
            status_box.update(label="Research Workflow Completed Successfully!", state="complete", expanded=False)
            st.toast("Research Report Ready!", icon="🎉")
            st.rerun()

        except Exception as exc:
            st.session_state.is_running = False
            status_box.update(label=f"Workflow Failed: {exc}", state="error", expanded=True)
            st.error(f"Error during research workflow: {exc}")


# ==============================================================================
# REPORT AND EVIDENCE DISPLAY TABS
# ==============================================================================
active_session: ResearchSession = st.session_state.current_session

if active_session:
    st.markdown("---")

    # Header with metadata badges
    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        st.markdown(f"### 📋 Research: *{active_session.question}*")
        st.caption(f"Session ID: `{active_session.session_id}` | Depth: `{active_session.depth}` | Status: `{active_session.status}`")
    with h_col2:
        if active_session.report and active_session.report.full_markdown:
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                st.download_button(
                    label="📥 .MD",
                    data=active_session.report.full_markdown,
                    file_name=f"research_{active_session.session_id[:8]}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with dl_col2:
                st.download_button(
                    label="📥 .TXT",
                    data=active_session.report.full_markdown,
                    file_name=f"research_{active_session.session_id[:8]}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

    # 4 Main Tabs
    tab_report, tab_sources, tab_analysis, tab_plan = st.tabs(
        [
            "📄 Research Report",
            f"🌐 Verified Sources ({len(active_session.sources)})",
            "🔬 Evidence Analysis",
            "🗺️ Research Plan",
        ]
    )

    # TAB 1: Final Rendered Report
    with tab_report:
        if active_session.report and active_session.report.full_markdown:
            st.markdown(active_session.report.full_markdown)
        elif active_session.status == "failed":
            st.error(f"Research failed: {active_session.error_message}")
        else:
            st.info("Report generation in progress or pending.")

    # TAB 2: Verified Sources
    with tab_sources:
        if not active_session.sources:
            st.info("No sources retrieved yet.")
        else:
            st.caption(f"Retrieved and deduplicated {len(active_session.sources)} sources from DuckDuckGo.")
            for i, src in enumerate(active_session.sources, 1):
                st.markdown(
                    f"""
                    <div class="source-item">
                        <div class="source-title">[{i}] {src.title}</div>
                        <a href="{src.url}" target="_blank" class="source-link">{src.url}</a>
                        <div class="source-snippet">{src.snippet}</div>
                        <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">
                            Query: <i>"{src.relevant_query or 'General'}"</i>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # TAB 3: Evidence Analysis
    with tab_analysis:
        if not active_session.analysis:
            st.info("Evidence analysis pending.")
        else:
            ana = active_session.analysis

            # Key Findings
            st.markdown("#### 🔑 Key Empirical Findings")
            for f in ana.key_findings:
                badge_type = "chip-completed" if f.is_factual else "chip-running"
                tag_label = "FACT" if f.is_factual else "INTERPRETATION"
                st.markdown(
                    f"""
                    <div class="card-box">
                        <span class="stage-chip {badge_type}">{tag_label}</span>
                        <b>{f.theme}</b> (Confidence: <i>{f.confidence}</i>)
                        <p style="margin-top: 0.35rem; color: #cbd5e1;">{f.statement}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Two columns for Themes & Limitations
            a_col1, a_col2 = st.columns(2)
            with a_col1:
                st.markdown("#### 🔄 Recurring Themes")
                if ana.recurring_themes:
                    for th in ana.recurring_themes:
                        st.write(f"- {th}")
                else:
                    st.caption("No recurring patterns flagged.")

                st.markdown("#### ⚠️ Information Gaps")
                if ana.information_gaps:
                    for gap in ana.information_gaps:
                        st.write(f"- {gap}")
                else:
                    st.caption("No significant gaps detected.")

            with a_col2:
                st.markdown("#### ⚖️ Conflicting Evidence")
                if ana.conflicting_evidence:
                    for conf in ana.conflicting_evidence:
                        st.write(f"- {conf}")
                else:
                    st.caption("No major direct contradictions identified.")

                st.markdown("#### 🔍 Weak Sources / Caveats")
                if ana.weak_sources:
                    for weak in ana.weak_sources:
                        st.write(f"- {weak}")
                else:
                    st.caption("All sources met baseline snippet quality.")

            st.markdown("#### 📝 Synthesis Notes")
            st.info(ana.synthesis_notes)

    # TAB 4: Research Plan
    with tab_plan:
        if not active_session.plan:
            st.info("Research plan pending.")
        else:
            plan = active_session.plan
            st.markdown(f"**Topic**: `{plan.topic}`")

            st.markdown("#### 🎯 Objectives")
            for obj in plan.research_objectives:
                st.write(f"- {obj}")

            st.markdown("#### ❓ Subquestions")
            for subq in plan.subquestions:
                st.write(f"- {subq}")

            st.markdown("#### 🔎 Generated DuckDuckGo Queries")
            for q in plan.search_queries:
                st.code(q, language="text")

            st.markdown("#### 📊 Expected Evidence Types")
            for ev in plan.expected_evidence:
                st.write(f"- {ev}")
