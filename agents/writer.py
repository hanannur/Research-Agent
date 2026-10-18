"""
Agent 4: Research Report Writer
Synthesizes the complete research cycle (Question -> Plan -> Sources -> Analysis)
into a publication-grade Markdown research report with verified source citations.
"""

import logging
import re
from typing import Optional

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel

from config import GEMINI_MODEL
from models.schemas import (
    AnalysisResult,
    ReportReference,
    ResearchPlan,
    ResearchReport,
    SourceRecord,
)

logger = logging.getLogger(__name__)

WRITER_SYSTEM_PROMPT = """You are an elite Academic and Technical Research Writer in the DeepResearch AI system.
Your mission is to produce a comprehensive, publication-grade Markdown research report.

REPORT STRUCTURE:
1. Title
2. Executive Summary
3. Research Question & Objectives
4. Methodology (explain multi-agent collaboration, DuckDuckGo web retrieval, and evidence filtering)
5. Key Findings (synthesize findings with inline citations like [1], [2])
6. Detailed Analysis (explore themes in depth, citing sources)
7. Conflicting Evidence & Limitations (candid assessment of contradictions, bias, snippet limits)
8. Conclusion (key takeaways, implications, and future outlook)
9. Numbered References (ONLY cite real URLs from the provided source list)

CITATION INTEGRITY RULES:
- Use numbered brackets like [1], [2] throughout the narrative.
- Every citation MUST correspond to a source in the provided Source Registry.
- DO NOT invent URLs or cite imaginary papers.
- Do not make absolute factual claims that are unsupported by the sources.

Output a validated ResearchReport model.
"""


def create_writer_agent(model_name: Optional[str] = None, custom_model=None) -> Agent:
    """Instantiates the Research Report Writer Agent with PydanticAI."""
    model = custom_model or GoogleModel(model_name or GEMINI_MODEL)
    return Agent(
        model=model,
        output_type=ResearchReport,
        system_prompt=WRITER_SYSTEM_PROMPT,
    )


def reconcile_and_audit_references(
    report: ResearchReport,
    source_registry: list[SourceRecord],
) -> ResearchReport:
    """
    Audits the report references against the verified source registry.
    Ensures that every reference points to a genuine URL retrieved by the web search tool,
    preventing hallucinated references.
    """
    valid_urls = {s.url.strip(): s for s in source_registry if s.url}

    verified_refs: list[ReportReference] = []
    seen_urls: set[str] = set()

    # First, reconcile any references proposed by the LLM
    for ref in report.references:
        url = ref.url.strip()
        if url in valid_urls and url not in seen_urls:
            matched_source = valid_urls[url]
            seen_urls.add(url)
            verified_refs.append(
                ReportReference(
                    index=len(verified_refs) + 1,
                    title=matched_source.title,
                    url=matched_source.url,
                    snippet=matched_source.snippet,
                )
            )

    # If the LLM omitted some valid sources or fabricated all of them,
    # populate directly from the real source registry to guarantee accuracy
    if len(verified_refs) == 0 and len(source_registry) > 0:
        for idx, src in enumerate(source_registry, 1):
            verified_refs.append(
                ReportReference(
                    index=idx,
                    title=src.title,
                    url=src.url,
                    snippet=src.snippet,
                )
            )
    else:
        # Add any unreferenced real sources up to a reasonable count
        for src in source_registry:
            if src.url not in seen_urls and len(verified_refs) < 15:
                seen_urls.add(src.url)
                verified_refs.append(
                    ReportReference(
                        index=len(verified_refs) + 1,
                        title=src.title,
                        url=src.url,
                        snippet=src.snippet,
                    )
                )

    report.references = verified_refs
    report.full_markdown = report.assemble_markdown()
    return report


def write_research_report(
    question: str,
    plan: ResearchPlan,
    sources: list[SourceRecord],
    analysis: AnalysisResult,
    agent: Optional[Agent] = None,
    custom_model=None,
) -> ResearchReport:
    """
    Synthesizes the complete research cycle and produces a validated, audited report.
    """
    writer = agent or create_writer_agent(custom_model=custom_model)

    # Build numbered source registry text
    registry_lines = []
    for i, s in enumerate(sources, 1):
        registry_lines.append(f"[{i}] Title: {s.title}\n    URL: {s.url}\n    Snippet: {s.snippet[:180]}...")
    registry_text = "\n".join(registry_lines) if registry_lines else "No external sources retrieved."

    # Build analysis summary text
    findings_lines = []
    for f in analysis.key_findings:
        fact_tag = "FACT" if f.is_factual else "INTERPRETATION"
        findings_lines.append(f"- [{fact_tag}] {f.statement} (Sources: {', '.join(f.source_urls) if f.source_urls else 'General'})")
    findings_text = "\n".join(findings_lines) if findings_lines else "None recorded."

    prompt = f"""RESEARCH QUESTION:
"{question}"

RESEARCH PLAN:
Topic: {plan.topic}
Objectives: {", ".join(plan.research_objectives)}
Subquestions:
- """ + "\n- ".join(plan.subquestions) + f"""

VERIFIED SOURCE REGISTRY ({len(sources)} sources):
{registry_text}

EVIDENCE ANALYSIS FINDINGS:
{findings_text}

Recurring Themes: {", ".join(analysis.recurring_themes)}
Conflicting Evidence: {", ".join(analysis.conflicting_evidence)}
Weak Sources / Caveats: {", ".join(analysis.weak_sources)}
Information Gaps: {", ".join(analysis.information_gaps)}
Synthesis: {analysis.synthesis_notes}

Write a comprehensive, professional research report in Markdown.
Ensure all sections are well-developed with thorough paragraphs and specific citations like [1], [2] linked to the verified source registry."""

    result = writer.run_sync(prompt)
    report: ResearchReport = result.output

    # Audit and reconcile references against the verified source registry
    audited_report = reconcile_and_audit_references(report, sources)
    return audited_report
