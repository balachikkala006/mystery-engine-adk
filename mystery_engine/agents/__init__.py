"""Multi-agent orchestration package for the Interactive AI Mystery Engine."""

from mystery_engine.agents.case_forge import create_case_forge_pipeline
from mystery_engine.agents.director import create_mystery_director
from mystery_engine.agents.model_router import select_model_for_role
from mystery_engine.agents.specialists import (
    create_forensics_analyst,
    create_suspect_interrogator,
    create_verdict_judge,
)

__all__ = [
    "create_case_forge_pipeline",
    "create_forensics_analyst",
    "create_mystery_director",
    "create_suspect_interrogator",
    "create_verdict_judge",
    "select_model_for_role",
]
