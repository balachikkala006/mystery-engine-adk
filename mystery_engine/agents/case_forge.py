"""CaseForgePipeline: Sequential -> Parallel -> Loop ADK workflow for custom mysteries.

Uses Strategic Model Routing (`select_model_for_role`) to assign the higher-reasoning
`planning_model` to worldbuilding, suspect profiling, structured lore critique
(`output_schema=LoreCritiqueReport`), and case refinement.

Architecture:
    CaseForgePipeline (SequentialAgent)
    ├── WorldBuilderParallel (ParallelAgent)
    │   ├── SceneArchitectAgent  -> writes `draft_scene` (planning tier)
    │   └── SuspectProfilerAgent -> writes `draft_suspects` (planning tier)
    └── ConsistencyRefinementLoop (LoopAgent, max_iterations=2)
        ├── LoreCriticAgent      -> structured `LoreCritiqueReport` JSON (`lore_critique`)
        └── CaseRefinerAgent     -> finalizes via `start_new_case` + `exit_refinement_loop`
"""

from __future__ import annotations

from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent

from mystery_engine.agents.model_router import select_model_for_role
from mystery_engine.config import Settings, get_settings
from mystery_engine.schemas import LoreCritiqueReport
from mystery_engine.tools.case_tools import exit_refinement_loop, start_new_case


def create_case_forge_pipeline(
    model: str | None = None,
    settings: Settings | None = None,
) -> SequentialAgent:
    """Build the multi-stage custom mystery generator workflow."""
    cfg = settings or get_settings()
    planning_model = select_model_for_role("planning", settings=cfg, override=model)
    critique_model = select_model_for_role("critique", settings=cfg, override=model)

    scene_architect = LlmAgent(
        name="SceneArchitectAgent",
        model=planning_model,
        description="Designs the crime scene setting, victim background, and 3-4 forensic clues.",
        instruction=(
            "You are the Scene Architect for an interactive detective game. "
            "Based on the user's requested mystery theme, design an evocative setting, "
            "a clear victim and time of crime (HH:MM), and 3 to 4 numbered clues "
            "(clue_1, clue_2, clue_3, clue_4). Each clue must have a title, location, "
            "surface_description, and hidden forensic_detail. Return concise structured notes."
        ),
        output_key="draft_scene",
    )

    suspect_profiler = LlmAgent(
        name="SuspectProfilerAgent",
        model=planning_model,
        description="Creates three distinct suspects with motives, alibis, and secrets.",
        instruction=(
            "You are the Suspect Profiler for an interactive detective game. "
            "Based on the user's requested mystery theme, craft exactly 3 distinct suspects. "
            "For each suspect specify: name, role, personality, claimed_alibi, alibi_window, "
            "secret, motive, and a unique fingerprint_id (e.g. FP-NAME-101). "
            "Designate exactly ONE suspect as the true culprit with a breakable alibi."
        ),
        output_key="draft_suspects",
    )

    world_builder_parallel = ParallelAgent(
        name="WorldBuilderParallel",
        description="Concurrently drafts crime-scene clues and suspect profiles.",
        sub_agents=[scene_architect, suspect_profiler],
    )

    lore_critic = LlmAgent(
        name="LoreCriticAgent",
        model=critique_model,
        description="Audits drafted mystery scenes and suspects and emits a strict JSON critique.",
        instruction=(
            "You are the Lore Consistency Critic. Review the drafted scene and suspects below:\n\n"
            "DRAFT SCENE:\n{draft_scene?}\n\n"
            "DRAFT SUSPECTS:\n{draft_suspects?}\n\n"
            "Verify that:\n"
            "1. Exactly one suspect is the culprit and at least two clues point to them.\n"
            "2. Innocent suspects have plausible motives/secrets without breaking the timeline.\n"
            "3. All clue IDs and suspect names match cleanly.\n\n"
            "Return a structured LoreCritiqueReport JSON object."
        ),
        output_schema=LoreCritiqueReport,
        output_key="lore_critique",
    )

    case_refiner = LlmAgent(
        name="CaseRefinerAgent",
        model=planning_model,
        description="Refines and commits the validated mystery dossier into session state.",
        instruction=(
            "You are the Case Refiner. Combine {draft_scene?}, {draft_suspects?}, and "
            "resolve any issues listed in {lore_critique?}.\n\n"
            "Build a valid JSON string matching CaseDossier (case_id, title, theme, "
            "difficulty, setting, victim, time_of_crime, opening_brief, suspects, clues, "
            "solution with culprit_name, true_motive, method, key_clue_ids) and call "
            "`start_new_case(theme=..., difficulty=..., custom_case_json=...)`.\n\n"
            "Immediately after `start_new_case` succeeds, call `exit_refinement_loop` with a "
            "one-sentence summary, then present ONLY the player-safe opening briefing, "
            "suspect list, and available clues (NEVER reveal the culprit or sealed solution)."
        ),
        tools=[start_new_case, exit_refinement_loop],
    )

    consistency_loop = LoopAgent(
        name="ConsistencyRefinementLoop",
        description="Iteratively critiques and refines custom mystery lore until consistent.",
        sub_agents=[lore_critic, case_refiner],
        max_iterations=2,
    )

    return SequentialAgent(
        name="CaseForgePipeline",
        description=(
            "Generates a brand-new custom mystery case using parallel worldbuilding "
            "followed by an iterative lore-consistency critic/refiner loop."
        ),
        sub_agents=[world_builder_parallel, consistency_loop],
    )
