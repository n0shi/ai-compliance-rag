"""Structured schemas for the agent."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, field_validator

ToolName = Literal["search_kb", "penalty_calculator", "deadline_calculator", "external_lookup"]

class Citation(BaseModel):
    doc_id: str
    chunk_id: str
    quote: str
    doc_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    source_role: str | None = None

class ToolCall(BaseModel):
    tool_name: ToolName
    arguments: dict = Field(default_factory=dict)
    success: bool = True
    observation_summary: str = ""

class AgentAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    abstained: bool = False
    reasoning_trace: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    @field_validator("answer")
    @classmethod
    def answer_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip(): raise ValueError("answer must not be empty")
        return v.strip()

class GuardrailDecision(BaseModel):
    allowed: bool
    reason: str = ""
    category: Literal["ok", "off_topic", "personal_data", "prompt_injection", "missing_citations", "low_confidence", "invalid_json"] = "ok"

class PenaltyCalculation(BaseModel):
    law: Literal["AI Act", "GDPR"]
    violation_type: str
    annual_turnover_eur: float | None = None
    fixed_cap_eur: float
    turnover_percent: float | None = None
    turnover_based_eur: float | None = None
    maximum_penalty_eur: float
    calculation: str
    caveat: str

class DeadlineCalculation(BaseModel):
    event: str
    start_date: str
    months_after_start: int
    deadline_date: str
    reference_date: str
    days_remaining: int
    status: Literal["past", "today", "future"]
    caveat: str
