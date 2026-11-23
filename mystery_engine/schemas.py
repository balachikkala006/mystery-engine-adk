"""Strongly-typed Pydantic input/output JSON schemas for the Mystery Engine.

Enforces strict argument validation on ADK FunctionTools and structured LLM outputs
(e.g., `LoreCritiqueReport` attached as `output_schema` on `LoreCriticAgent`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Clue(BaseModel):
    """A physical or digital piece of evidence at the crime scene."""

    clue_id: str = Field(..., min_length=1, description="Unique clue identifier, e.g. 'clue_1'.")
    title: str = Field(..., min_length=1, description="Short player-facing name of the clue.")
    location: str = Field(..., min_length=1, description="Where the clue was found.")
    surface_description: str = Field(
        ..., min_length=1, description="What any observer notices at first glance."
    )
    forensic_detail: str = Field(
        ..., min_length=1, description="Hidden detail unlocked upon careful inspection."
    )
    fingerprint_sample: str | None = Field(
        default=None, description="Optional fingerprint sample ID for MCP lab analysis."
    )
    cipher_text: str | None = Field(
        default=None, description="Optional encoded string for MCP cipher decoding."
    )
    links_to_suspect: str | None = Field(
        default=None, description="Suspect name this clue implicates (never shown raw)."
    )


class Suspect(BaseModel):
    """An autonomous suspect profile for interrogation."""

    name: str = Field(..., min_length=1, description="Full suspect name.")
    role: str = Field(..., min_length=1, description="Relationship to the victim or setting.")
    personality: str = Field(..., min_length=1, description="Tone and demeanor during questioning.")
    claimed_alibi: str = Field(..., min_length=1, description="Alibi the suspect initially offers.")
    alibi_window: str = Field(..., min_length=1, description="Time window claimed, e.g. '21:15-21:45'.")
    secret: str = Field(..., min_length=1, description="Something the suspect hides even if innocent.")
    motive: str = Field(..., min_length=1, description="Potential motive for the crime.")
    fingerprint_id: str = Field(..., min_length=1, description="Reference ID in the forensics lab.")


class SealedSolution(BaseModel):
    """Ground truth kept hidden from the player until final verdict."""

    culprit_name: str = Field(..., min_length=1, description="Exact name of the true culprit.")
    true_motive: str = Field(..., min_length=1, description="Actual motive behind the crime.")
    method: str = Field(..., min_length=1, description="How the culprit carried out the crime.")
    key_clue_ids: list[str] = Field(
        default_factory=list, description="Clue IDs that decisively prove guilt."
    )


class CaseDossier(BaseModel):
    """Complete interactive mystery case stored in ADK session state."""

    case_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    theme: str = Field(..., min_length=1)
    difficulty: Literal["easy", "standard", "hard"] = "standard"
    setting: str = Field(..., min_length=1)
    victim: str = Field(..., min_length=1)
    time_of_crime: str = Field(..., min_length=1)
    opening_brief: str = Field(..., min_length=1)
    suspects: list[Suspect] = Field(..., min_length=1)
    clues: list[Clue] = Field(..., min_length=1)
    solution: SealedSolution

    def public_summary(self) -> dict:
        """Return player-safe case overview without leaking the sealed solution."""
        return {
            "case_id": self.case_id,
            "title": self.title,
            "theme": self.theme,
            "difficulty": self.difficulty,
            "setting": self.setting,
            "victim": self.victim,
            "time_of_crime": self.time_of_crime,
            "opening_brief": self.opening_brief,
            "suspects": [
                {
                    "name": s.name,
                    "role": s.role,
                    "claimed_alibi": s.claimed_alibi,
                    "alibi_window": s.alibi_window,
                }
                for s in self.suspects
            ],
            "available_clues": [
                {
                    "clue_id": c.clue_id,
                    "title": c.title,
                    "location": c.location,
                    "surface_description": c.surface_description,
                }
                for c in self.clues
            ],
        }


# ---------------------------------------------------------------------------
# Explicit Tool Input & Output JSON Schemas
# ---------------------------------------------------------------------------


class StartCaseInput(BaseModel):
    """Validated input schema for `start_new_case`."""

    model_config = ConfigDict(str_strip_whitespace=True)

    theme: str = Field(default="noir", min_length=1, max_length=80)
    difficulty: Literal["easy", "standard", "hard"] = "standard"
    custom_case_json: str = ""


class InspectClueInput(BaseModel):
    """Validated input schema for `inspect_clue`."""

    model_config = ConfigDict(str_strip_whitespace=True)

    clue_id: str = Field(..., min_length=1, max_length=64)


class ClueInspectionOutput(BaseModel):
    """Strict output schema returned by `inspect_clue`."""

    status: Literal["success"] = "success"
    already_inspected: bool
    clue_id: str
    title: str
    location: str
    surface_description: str
    forensic_detail: str
    fingerprint_sample: str | None = None
    cipher_text: str | None = None
    total_discovered: int = Field(ge=0)
    total_clues: int = Field(ge=1)


class InterrogationNoteInput(BaseModel):
    """Validated input schema for `record_interrogation_note`."""

    model_config = ConfigDict(str_strip_whitespace=True)

    suspect_name: str = Field(..., min_length=1, max_length=120)
    summary: str = Field(..., min_length=3, max_length=500)
    contradiction_spotted: bool = False


class AccusationInput(BaseModel):
    """Validated input schema for the high-stakes `submit_accusation` tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    suspect_name: str = Field(..., min_length=1, max_length=120)
    motive: str = Field(..., min_length=3, max_length=600)
    key_evidence_ids: list[str] = Field(default_factory=list)
    confirmed_by_detective: bool = False

    @field_validator("key_evidence_ids")
    @classmethod
    def normalize_evidence_ids(cls, values: list[str]) -> list[str]:
        return [v.strip() for v in values if v and v.strip()]


class AccusationResult(BaseModel):
    """Structured outcome of a detective's final accusation."""

    verdict: Literal["solved", "wrong_suspect", "case_failed"]
    score: int = Field(ge=0, le=100)
    attempts_remaining: int = Field(ge=0)
    feedback: str
    revealed_solution: SealedSolution | None = None


class LoreCritiqueReport(BaseModel):
    """Structured LLM `output_schema` emitted by `LoreCriticAgent`."""

    approved: bool = Field(
        ..., description="True only if clues, alibis, and culprit timeline are airtight."
    )
    culprit_consistency_ok: bool = Field(
        ..., description="True if at least two clues cleanly point to exactly one culprit."
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Concrete plot holes or timeline contradictions to fix before launch.",
    )
    summary: str = Field(..., description="One-sentence summary of the lore audit verdict.")
