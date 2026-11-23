"""Automated ADK evaluation schema validation and live AgentEvaluator test."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

EVALS_DIR = Path(__file__).resolve().parent.parent / "evals"
EVALSET_PATH = EVALS_DIR / "mystery_engine.evalset.json"
EVAL_CONFIG_PATH = EVALS_DIR / "test_config.json"


def test_evalset_and_config_are_valid_adk_schema():
    """Offline check ensuring evalset JSON conforms to ADK's EvalSet schema."""
    raw_evalset = json.loads(EVALSET_PATH.read_text(encoding="utf-8"))
    raw_config = json.loads(EVAL_CONFIG_PATH.read_text(encoding="utf-8"))

    assert raw_evalset["eval_set_id"] == "mystery_engine_core_regression"
    assert len(raw_evalset["eval_cases"]) >= 3
    assert "tool_trajectory_avg_score" in raw_config["criteria"]

    from google.adk.evaluation.eval_set import EvalSet

    parsed = EvalSet.model_validate(raw_evalset)
    assert parsed.eval_set_id == "mystery_engine_core_regression"
    assert len(parsed.eval_cases) == len(raw_evalset["eval_cases"])


@pytest.mark.eval
@pytest.mark.skipif(
    not (os.getenv("GOOGLE_API_KEY") and os.getenv("RUN_LIVE_EVALS") == "1"),
    reason="Set RUN_LIVE_EVALS=1 and GOOGLE_API_KEY to execute live ADK AgentEvaluator tests",
)
async def test_live_adk_agent_evaluator():
    """Run Google ADK AgentEvaluator against the golden mystery_engine evalset."""
    from google.adk.evaluation.agent_evaluator import AgentEvaluator

    await AgentEvaluator.evaluate(
        agent_module="mystery_engine.agent",
        eval_dataset_file_path_or_dir=str(EVALSET_PATH),
    )
