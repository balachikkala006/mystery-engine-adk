"""Unit tests for typed ADK case tools, HITL confirmation hooks, and guided errors."""

from __future__ import annotations

import json

from mystery_engine.cases import get_curated_case
from mystery_engine.tools.case_tools import (
    compute_detective_rank,
    exit_refinement_loop,
    inspect_clue,
    list_case_status,
    record_interrogation_note,
    start_new_case,
    submit_accusation,
)
from tests.conftest import DummyToolConfirmation


def test_start_new_case_initializes_session_and_user_state(tool_context):
    result = start_new_case(theme="noir", difficulty="hard", tool_context=tool_context)

    assert result["status"] == "success"
    assert result["case"]["title"] == "The Midnight Horologist"
    assert result["case"]["difficulty"] == "hard"
    assert "solution" not in result["case"]
    assert tool_context.state["active_case"]["case_id"] == "case_noir_clocktower"
    assert tool_context.state["sealed_solution"]["culprit_name"] == "Marcus Sterling"
    assert tool_context.state["user:detective_rank"] == "Rookie Investigator"
    assert tool_context.state["discovered_clues"] == []


def test_start_new_case_supports_scifi_and_custom_json_fallback(tool_context):
    scifi = start_new_case(theme="scifi orbital", tool_context=tool_context)
    assert scifi["case"]["case_id"] == "case_scifi_orbital"

    custom = get_curated_case("noir")
    custom.title = "Custom Harbor Enigma"
    res_custom = start_new_case(
        theme="custom",
        custom_case_json=json.dumps(custom.model_dump()),
        tool_context=tool_context,
    )
    assert res_custom["case"]["title"] == "Custom Harbor Enigma"

    res_fallback = start_new_case(
        theme="noir",
        custom_case_json="{not-valid-json",
        tool_context=tool_context,
    )
    assert res_fallback["status"] == "success"
    assert res_fallback["case"]["case_id"] == "case_noir_clocktower"


def test_inspect_clue_tracks_discoveries_and_returns_guided_errors(tool_context):
    no_case = inspect_clue("clue_1", tool_context)
    assert no_case["status"] == "error"
    assert "start_new_case" in no_case["recovery_action"]

    start_new_case(theme="noir", tool_context=tool_context)
    first = inspect_clue("clue_1", tool_context)
    assert first["status"] == "success"
    assert first["already_inspected"] is False
    assert first["fingerprint_sample"] == "FP-STERLING-209"
    assert first["total_discovered"] == 1

    repeat = inspect_clue("clue_1", tool_context)
    assert repeat["already_inspected"] is True
    assert repeat["total_discovered"] == 1

    missing = inspect_clue("clue_999", tool_context)
    assert missing["status"] == "error"
    assert "clue_1" in missing["available_clue_ids"]
    assert "recovery_action" in missing


def test_record_interrogation_note_and_case_status(tool_context):
    empty_status = list_case_status(tool_context)
    assert empty_status["has_active_case"] is False

    start_new_case(theme="noir", tool_context=tool_context)
    inspect_clue("clue_2", tool_context)
    note = record_interrogation_note(
        suspect_name="Marcus Sterling",
        summary="Insisted he was on the East Balcony phone at 21:30.",
        contradiction_spotted=True,
        tool_context=tool_context,
    )
    assert note["status"] == "success"
    assert note["total_notes"] == 1

    status = list_case_status(tool_context)
    assert status["has_active_case"] is True
    assert status["discovered_clues"] == ["clue_2"]
    assert "clue_1" in status["undiscovered_clues"]
    assert len(status["interrogation_notes"]) == 1


def test_submit_accusation_hitl_confirmation_pause_and_cancel(tool_context):
    start_new_case(theme="noir", tool_context=tool_context)

    # First call without confirmation must trigger ADK HITL request_confirmation pause
    paused = submit_accusation(
        suspect_name="Marcus Sterling",
        motive="Gambling debts due at midnight.",
        key_evidence_ids=["clue_1", "clue_2"],
        tool_context=tool_context,
        confirmed_by_detective=False,
    )
    assert paused["status"] == "pending_confirmation"
    assert paused["requires_human_confirmation"] is True
    assert len(tool_context.confirmation_requests) == 1
    assert tool_context.state["accusation_attempts"] == 0

    # Human rejects confirmation -> cancelled cleanly with zero attempts spent
    tool_context.tool_confirmation = DummyToolConfirmation(confirmed=False)
    cancelled = submit_accusation(
        suspect_name="Marcus Sterling",
        motive="Gambling debts due at midnight.",
        key_evidence_ids=["clue_1", "clue_2"],
        tool_context=tool_context,
    )
    assert cancelled["status"] == "cancelled"
    assert tool_context.state["accusation_attempts"] == 0


def test_submit_accusation_solves_case_via_adk_tool_confirmation(tool_context):
    start_new_case(theme="noir", tool_context=tool_context)
    tool_context.tool_confirmation = DummyToolConfirmation(confirmed=True)

    res = submit_accusation(
        suspect_name="Marcus Sterling",
        motive="He needed to steal the Chronometer to clear his midnight gambling debts.",
        key_evidence_ids=["clue_1", "clue_2", "clue_3"],
        tool_context=tool_context,
    )

    assert res["status"] == "success"
    assert res["verdict"] == "solved"
    assert res["score"] == 100
    assert res["cases_solved"] == 1
    assert res["detective_rank"] == "Senior Detective"
    assert res["revealed_solution"]["culprit_name"] == "Marcus Sterling"
    assert tool_context.state["case_closed"] is True

    closed_again = submit_accusation(
        "Clara Vance",
        "motive details",
        ["clue_1"],
        tool_context,
        confirmed_by_detective=True,
    )
    assert closed_again["status"] == "error"
    assert "recovery_action" in closed_again


def test_submit_accusation_handles_wrong_attempts_and_failure(tool_context):
    start_new_case(theme="noir", tool_context=tool_context)

    wrong_1 = submit_accusation(
        "Clara Vance",
        "forgery threat",
        ["clue_4"],
        tool_context,
        confirmed_by_detective=True,
    )
    assert wrong_1["verdict"] == "wrong_suspect"
    assert wrong_1["attempts_remaining"] == 1
    assert wrong_1["revealed_solution"] is None
    assert tool_context.state["case_closed"] is False

    wrong_2 = submit_accusation(
        "Dr. Elena Rostova",
        "cut out of will",
        ["clue_4"],
        tool_context,
        confirmed_by_detective=True,
    )
    assert wrong_2["verdict"] == "case_failed"
    assert wrong_2["attempts_remaining"] == 0
    assert wrong_2["revealed_solution"]["culprit_name"] == "Marcus Sterling"
    assert tool_context.state["case_closed"] is True


def test_exit_refinement_loop_sets_escalate_action(tool_context):
    result = exit_refinement_loop("Timeline and clue links verified.", tool_context)
    assert result["status"] == "success"
    assert result["escalated"] is True
    assert tool_context.actions.escalate is True
    assert tool_context.state["temp:lore_approved"] is True


def test_detective_rank_progression():
    assert compute_detective_rank(0) == "Rookie Investigator"
    assert compute_detective_rank(1) == "Senior Detective"
    assert compute_detective_rank(3) == "Chief Inspector"
    assert compute_detective_rank(5) == "Master Sleuth"
