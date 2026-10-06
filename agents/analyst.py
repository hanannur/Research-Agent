"""
Agent 3: Evidence Analyst
Synthesizes verified search sources against the research plan.
Extracts empirical findings, maps supporting source URLs, identifies contradictions,
evaluates source credibility, and separates sourced facts from interpretation.
"""

import json
import logging
from typing import Optional

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel

from config import GEMINI_MODEL
from models.schemas import AnalysisResult, FindingItem, ResearchPlan, SourceRecord

logger = logging.getLogger(__name__)

ANALYST_SYSTEM_PROMPT = """You are the Evidence Analyst in the DeepResearch AI system, specialized in AI Systems & Software Engineering Research.
Your job is to rigorously analyze real web search sources and technical/academic records collected for a research plan.

CRITICAL INTEGRITY & ANALYSIS RULES:
1. ONLY use evidence and facts present in the provided source records. DO NOT invent citations, statistics, or URLs.
2. Evaluate technical rigor: distinguish empirical benchmarks, protocol specs, and verified architecture patterns from promotional or marketing claims.
3. Note that sources are search snippets or paper abstracts; candidly acknowledge when snippets are brief or missing operational nuances.
4. Every finding item MUST map its supporting source URLs to the EXACT URLs provided in the source records.
5. Clearly distinguish sourced empirical facts (is_factual = True) from your analytical deductions and architectural trade-offs (is_factual = False).
6. Actively identify technical disagreements, architectural trade-offs, weak or shallow snippets, and remaining engineering/research gaps.

Output a validated AnalysisResult model.
"""


def create_analyst_agent(model_name: Optional[str] = None, custom_model=None) -> Agent:
    """Instantiates the Evidence Analyst Agent with PydanticAI."""
    model = custom_model or GoogleModel(model_name or GEMINI_MODEL)
    return Agent(
        model=model,
        output_type=AnalysisResult,
        system_prompt=ANALYST_SYSTEM_PROMPT,
    )


def analyze_evidence(
    plan: ResearchPlan,
    sources: list[SourceRecord],
    agent: Optional[Agent] = None,
    custom_model=None,
) -> AnalysisResult:
    """
    Executes evidence analysis over the plan and retrieved web sources.
    """
    analyst = agent or create_analyst_agent(custom_model=custom_model)

    if not sources:
        logger.warning("No search sources provided to Evidence Analyst; creating gap analysis")
        return AnalysisResult(
            key_findings=[
                FindingItem(
                    theme="Data Availability",
                    statement="Web search returned zero usable snippets due to network rate limits or blocked access.",
                    source_urls=[],
                    confidence="Preliminary",
                    is_factual=False,
                )
            ],
            recurring_themes=["Evidence limitation"],
            conflicting_evidence=[],
            weak_sources=["Web search returned zero usable snippets."],
            information_gaps=[q for q in plan.subquestions],
            synthesis_notes="No web evidence was available. Analysis cannot substantiate claims without external sources.",
        )

    # Format source records clearly for the prompt
    sources_text_lines = []
    for i, s in enumerate(sources, 1):
        sources_text_lines.append(
            f"Source [{i}]:\n  Title: {s.title}\n  URL: {s.url}\n  Query: {s.relevant_query}\n  Snippet: {s.snippet}\n"
        )
    sources_text = "\n".join(sources_text_lines)

    prompt = f"""RESEARCH PLAN:
Topic: {plan.topic}
Objectives: {", ".join(plan.research_objectives)}
Subquestions:
- """ + "\n- ".join(plan.subquestions) + f"""

RETRIEVED WEB SOURCES ({len(sources)} sources):
{sources_text}

Perform a rigorous empirical analysis:
1. Group key findings by theme. Link each finding to its actual supporting source URL(s).
2. Distinguish sourced facts (is_factual=True) from interpretation (is_factual=False).
3. Identify contradictions or differences in perspective among sources.
4. Flag weak or shallow snippets.
5. Identify information gaps that remain unanswered.
6. Provide synthesis notes evaluating the overall evidence landscape."""

    result = analyst.run_sync(prompt)
    return result.output
