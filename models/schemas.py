"""
Pydantic data models for structured inputs and outputs across all research agents.
Provides strict validation, serialization, and typing guarantees.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class ResearchPlan(BaseModel):
    """Output schema for Agent 1: Research Planner."""
    topic: str = Field(..., description="The refined core research topic")
    research_objectives: list[str] = Field(
        ..., min_length=1, description="Primary research objectives and goals"
    )
    subquestions: list[str] = Field(
        ..., min_length=2, max_length=6, description="2 to 6 focused subquestions addressing the topic"
    )
    search_queries: list[str] = Field(
        ..., min_length=2, max_length=8, description="Targeted DuckDuckGo search queries"
    )
    expected_evidence: list[str] = Field(
        ..., min_length=1, description="Types of concrete evidence expected to answer the queries"
    )


class SourceRecord(BaseModel):
    """Structured record for an individual web search result."""
    title: str = Field(..., description="Title of the webpage or article")
    url: str = Field(..., description="Verified direct URL of the source")
    snippet: str = Field(..., description="Explanatory text snippet returned by search")
    relevant_query: Optional[str] = Field(
        None, description="The search query that surfaced this source"
    )
    publication_date: Optional[str] = Field(
        None, description="Publication date or recency indicator if available"
    )
    source_type: str = Field(
        default="General Web",
        description="Source classification: Academic Paper / Preprint, Official Documentation, Engineering Blog / Technical Article, or General Web",
    )

    @field_validator("url")
    @classmethod
    def clean_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL protocol: {v}")
        return v


class FindingItem(BaseModel):
    """Granular finding with mapped evidence URLs and factuality distinction."""
    theme: str = Field(..., description="Category or thematic bucket")
    statement: str = Field(..., description="Clear finding statement")
    source_urls: list[str] = Field(
        default_factory=list, description="URLs from real search results supporting this finding"
    )
    confidence: str = Field(
        default="Medium", description="Confidence level: High, Medium, or Preliminary"
    )
    is_factual: bool = Field(
        default=True,
        description="True if directly supported by snippet facts; False if analytical interpretation",
    )


class AnalysisResult(BaseModel):
    """Output schema for Agent 3: Evidence Analyst."""
    key_findings: list[FindingItem] = Field(
        ..., min_length=1, description="Key empirical findings extracted from sources"
    )
    recurring_themes: list[str] = Field(
        default_factory=list, description="Recurring patterns observed across sources"
    )
    conflicting_evidence: list[str] = Field(
        default_factory=list, description="Contradictions or divergent perspectives between sources"
    )
    weak_sources: list[str] = Field(
        default_factory=list, description="Observations on lower-credibility or thin snippets"
    )
    information_gaps: list[str] = Field(
        default_factory=list, description="Unanswered questions or missing evidence"
    )
    synthesis_notes: str = Field(
        ..., description="Overall summary of the evidence landscape and analytical assessment"
    )


class ReportReference(BaseModel):
    """Numbered citation entry linking to a real verified source."""
    index: int = Field(..., description="Reference number [1], [2], etc.")
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    snippet: Optional[str] = Field(None, description="Brief snippet excerpt")


class ResearchReport(BaseModel):
    """Output schema for Agent 4: Research Report Writer."""
    title: str = Field(..., description="Report title")
    executive_summary: str = Field(..., description="High-level executive briefing")
    research_question_and_objectives: str = Field(..., description="Original question and scope")
    methodology: str = Field(..., description="Description of multi-agent and search methodology")
    key_findings: str = Field(..., description="Synthesized key findings with inline citations")
    detailed_analysis: str = Field(..., description="Detailed analytical breakdown across themes")
    conflicting_evidence_and_limitations: str = Field(
        ..., description="Contradictions, data limits, and uncertainties"
    )
    conclusion: str = Field(..., description="Actionable takeaways and future outlook")
    references: list[ReportReference] = Field(
        default_factory=list, description="Ordered source registry"
    )
    full_markdown: str = Field(
        default="", description="Complete rendered Markdown document"
    )

    def assemble_markdown(self) -> str:
        """Assembles all sections into a clean, presentation-ready Markdown document."""
        refs_md = []
        for ref in self.references:
            refs_md.append(f"{ref.index}. [{ref.title}]({ref.url})")
            if ref.snippet:
                refs_md.append(f"   > {ref.snippet[:200]}...")

        refs_text = "\n".join(refs_md) if refs_md else "_No external sources cited._"

        doc = f"""# {self.title}

## Executive Summary
{self.executive_summary}

---

## 1. Research Question & Objectives
{self.research_question_and_objectives}

## 2. Methodology
{self.methodology}

## 3. Key Findings
{self.key_findings}

## 4. Detailed Analysis
{self.detailed_analysis}

## 5. Conflicting Evidence & Limitations
{self.conflicting_evidence_and_limitations}

## 6. Conclusion
{self.conclusion}

---

## 7. References
{refs_text}
"""
        return doc.strip()


class ResearchSession(BaseModel):
    """Persistent research session record."""
    session_id: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    question: str
    depth: str = "Standard"
    status: str = "pending"  # pending, planning, researching, analyzing, writing, completed, failed
    error_message: Optional[str] = None
    plan: Optional[ResearchPlan] = None
    sources: list[SourceRecord] = Field(default_factory=list)
    analysis: Optional[AnalysisResult] = None
    report: Optional[ResearchReport] = None
