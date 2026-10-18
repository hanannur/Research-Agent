"""
Agent 1: Research Planner
Breaks down the user's research question into clear objectives,
focused subquestions, and targeted search queries.
"""

import logging
from typing import Optional

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel

from config import GEMINI_MODEL
from models.schemas import ResearchPlan

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are an expert Research Planning Specialist in the DeepResearch AI system.
Your responsibility:
1. Analyze the user's research question thoroughly.
2. Formulate 1-3 core research objectives.
3. Generate 3 to 6 focused, distinct subquestions that deconstruct the problem.
4. Craft 3 to 6 concrete, keyword-rich search queries suitable for web search (e.g. DuckDuckGo).
   - Avoid conversational queries like "Can you tell me about...".
   - Use direct search keywords, domain terminology, and recency terms (e.g. "2026", "trends", "benchmarks", "case studies").
5. Define the specific types of evidence needed (e.g., industry whitepapers, empirical benchmarks, practitioner surveys).

Be objective, thorough, and output a validated ResearchPlan model.
"""


def create_planner_agent(model_name: Optional[str] = None, custom_model=None) -> Agent:
    """Instantiates the Research Planner Agent with PydanticAI."""
    model = custom_model or GoogleModel(model_name or GEMINI_MODEL)
    return Agent(
        model=model,
        output_type=ResearchPlan,
        system_prompt=PLANNER_SYSTEM_PROMPT,
    )


def plan_research(
    question: str,
    depth: str = "Standard",
    agent: Optional[Agent] = None,
    custom_model=None,
) -> ResearchPlan:
    """
    Executes the planning phase for a research question.
    """
    planner = agent or create_planner_agent(custom_model=custom_model)
    prompt = f"""Research Question: "{question}"
Target Depth: {depth}

Produce a comprehensive research plan with objectives, 3-6 focused subquestions, and targeted search queries."""

    result = planner.run_sync(prompt)
    return result.output
