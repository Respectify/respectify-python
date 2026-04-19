"""Internal-only Perspective scoring schemas for backend use."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PerspectiveSpanScore(BaseModel):
    """A score for a specific span of text within the comment."""

    model_config = ConfigDict(frozen=True)

    begin: int = Field(..., ge=0, description="Start character position in the original comment")
    end: int = Field(..., ge=0, description="End character position in the original comment")
    score: float = Field(..., ge=0.0, le=1.0, description="Score for this span (0.0-1.0)")
    quoted_text: str = Field(..., description="The quoted text from the comment for this span")


class PerspectiveAttributeScore(BaseModel):
    """Score for a single internal Perspective attribute, with optional span-level detail."""

    model_config = ConfigDict(frozen=True)

    score: float = Field(..., ge=0.0, le=1.0, description="Summary score (0.0-1.0 probability)")
    span_scores: List[PerspectiveSpanScore] = Field(
        default_factory=list,
        description="Per-span scores identifying which parts of the comment triggered this attribute",
    )


class PerspectiveResult(BaseModel):
    """Internal Respectify Perspective result used by the native backend scorer."""

    model_config = ConfigDict(frozen=True)

    toxicity: Optional[PerspectiveAttributeScore] = Field(None)
    severe_toxicity: Optional[PerspectiveAttributeScore] = Field(None)
    identity_attack: Optional[PerspectiveAttributeScore] = Field(None)
    insult: Optional[PerspectiveAttributeScore] = Field(None)
    profanity: Optional[PerspectiveAttributeScore] = Field(None)
    threat: Optional[PerspectiveAttributeScore] = Field(None)
    sexually_explicit: Optional[PerspectiveAttributeScore] = Field(None)
    incoherent: Optional[PerspectiveAttributeScore] = Field(None)
    inflammatory: Optional[PerspectiveAttributeScore] = Field(None)
    spam: Optional[PerspectiveAttributeScore] = Field(None)
    reasoning: Optional[PerspectiveAttributeScore] = Field(None)
    curiosity: Optional[PerspectiveAttributeScore] = Field(None)
    nuance: Optional[PerspectiveAttributeScore] = Field(None)
    compassion: Optional[PerspectiveAttributeScore] = Field(None)
    constructiveness: Optional[PerspectiveAttributeScore] = Field(None)
    respect: Optional[PerspectiveAttributeScore] = Field(None)
    personal_story: Optional[PerspectiveAttributeScore] = Field(None)
    affinity: Optional[PerspectiveAttributeScore] = Field(None)
    flirtation: Optional[PerspectiveAttributeScore] = Field(None)
    summary: str = Field(..., description="One-sentence plain-language summary of the comment's character")


class PerspectiveRawScores(BaseModel):
    """Internal schema for LLM output before span resolution."""

    toxicity: float = Field(..., ge=0.0, le=1.0)
    toxicity_span: str = Field(default="", description="Quoted text from the comment most relevant to toxicity")
    severe_toxicity: float = Field(..., ge=0.0, le=1.0)
    severe_toxicity_span: str = Field(default="", description="Quoted text for severe toxicity")
    identity_attack: float = Field(..., ge=0.0, le=1.0)
    identity_attack_span: str = Field(default="", description="Quoted text for identity attack")
    insult: float = Field(..., ge=0.0, le=1.0)
    insult_span: str = Field(default="", description="Quoted text for insult")
    profanity: float = Field(..., ge=0.0, le=1.0)
    profanity_span: str = Field(default="", description="Quoted text for profanity")
    threat: float = Field(..., ge=0.0, le=1.0)
    threat_span: str = Field(default="", description="Quoted text for threat")
    sexually_explicit: float = Field(..., ge=0.0, le=1.0)
    sexually_explicit_span: str = Field(default="", description="Quoted text for sexually explicit")
    incoherent: float = Field(..., ge=0.0, le=1.0)
    incoherent_span: str = Field(default="", description="Quoted text for incoherent")
    inflammatory: float = Field(..., ge=0.0, le=1.0)
    inflammatory_span: str = Field(default="", description="Quoted text for inflammatory")
    spam: float = Field(..., ge=0.0, le=1.0)
    spam_span: str = Field(default="", description="Quoted text for spam")
    reasoning: float = Field(..., ge=0.0, le=1.0)
    reasoning_span: str = Field(default="", description="Quoted text for reasoning")
    curiosity: float = Field(..., ge=0.0, le=1.0)
    curiosity_span: str = Field(default="", description="Quoted text for curiosity")
    nuance: float = Field(..., ge=0.0, le=1.0)
    nuance_span: str = Field(default="", description="Quoted text for nuance")
    compassion: float = Field(..., ge=0.0, le=1.0)
    compassion_span: str = Field(default="", description="Quoted text for compassion")
    constructiveness: float = Field(..., ge=0.0, le=1.0)
    constructiveness_span: str = Field(default="", description="Quoted text for constructiveness")
    respect: float = Field(..., ge=0.0, le=1.0)
    respect_span: str = Field(default="", description="Quoted text for respect")
    personal_story: float = Field(..., ge=0.0, le=1.0)
    personal_story_span: str = Field(default="", description="Quoted text for personal story")
    affinity: float = Field(..., ge=0.0, le=1.0)
    affinity_span: str = Field(default="", description="Quoted text for affinity")
    flirtation: float = Field(..., ge=0.0, le=1.0)
    flirtation_span: str = Field(default="", description="Quoted text for flirtation")
    summary: str = Field(..., description="One-sentence summary")
