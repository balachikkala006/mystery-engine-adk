"""Structural tests verifying ADK topology, model routing, output schemas, A2A, and IaC."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent

from mystery_engine.agent import build_app
from mystery_engine.config import Settings
from mystery_engine.schemas import LoreCritiqueReport


def test_agent_hierarchy_model_routing_and_app_configuration():
    cfg = Settings(
        fast_model="gemini-3.5-flash",
        planning_model="gemini-3.8-flash",
        session_backend="memory",
        otel_exporter="none",
    )
    app = build_app(cfg, enable_mcp=False)

    assert app.name == "mystery_engine"
    assert app.events_compaction_config is not None
    assert app.events_compaction_config.compaction_interval == 4
    assert app.events_compaction_config.overlap_size == 1
    assert len(app.plugins) == 2

    director = app.root_agent
    assert isinstance(director, LlmAgent)
    assert director.name == "MysteryDirector"
    assert director.model == "gemini-3.5-flash"
    assert "## 1. Persona & Mission" in director.instruction
    assert "## 4. Non-Negotiable Constraints & Safety Rules" in director.instruction

    sub_by_name = {agent.name: agent for agent in director.sub_agents}
    assert set(sub_by_name.keys()) == {
        "CaseForgePipeline",
        "ForensicsAnalystAgent",
        "SuspectInterrogatorAgent",
        "VerdictJudgeAgent",
    }
    assert sub_by_name["ForensicsAnalystAgent"].model == "gemini-3.5-flash"
    assert sub_by_name["SuspectInterrogatorAgent"].model == "gemini-3.5-flash"
    assert sub_by_name["VerdictJudgeAgent"].model == "gemini-3.5-flash"

    # Verify SequentialAgent -> ParallelAgent + LoopAgent topology & Strategic Model Routing
    case_forge = sub_by_name["CaseForgePipeline"]
    assert isinstance(case_forge, SequentialAgent)
    assert len(case_forge.sub_agents) == 2
    assert isinstance(case_forge.sub_agents[0], ParallelAgent)
    assert isinstance(case_forge.sub_agents[1], LoopAgent)

    parallel_sub = {a.name: a for a in case_forge.sub_agents[0].sub_agents}
    assert set(parallel_sub.keys()) == {"SceneArchitectAgent", "SuspectProfilerAgent"}
    assert parallel_sub["SceneArchitectAgent"].model == "gemini-3.8-flash"
    assert parallel_sub["SuspectProfilerAgent"].model == "gemini-3.8-flash"

    loop_sub = case_forge.sub_agents[1].sub_agents
    assert [a.name for a in loop_sub] == ["LoreCriticAgent", "CaseRefinerAgent"]
    assert loop_sub[0].model == "gemini-3.8-flash"
    assert loop_sub[0].output_schema is LoreCritiqueReport
    assert loop_sub[1].model == "gemini-3.8-flash"


def test_terraform_iac_provisions_cloud_run_and_secret_manager():
    tf_main = (
        Path(__file__).resolve().parent.parent / "infra" / "terraform" / "main.tf"
    ).read_text(encoding="utf-8")
    assert 'resource "google_cloud_run_v2_service"' in tf_main
    assert 'resource "google_secret_manager_secret"' in tf_main
    assert "secret_key_ref" in tf_main


@pytest.mark.skipif(
    importlib.util.find_spec("a2a") is None,
    reason="a2a-sdk optional dependency not installed",
)
def test_a2a_server_builds_asgi_app():
    from mystery_engine.a2a_server import create_a2a_app

    a2a_app = create_a2a_app(host="127.0.0.1", port=8001)
    assert a2a_app is not None
