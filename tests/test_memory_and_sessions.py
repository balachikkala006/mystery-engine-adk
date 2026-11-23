"""Tests for persistent SQLite sessions, PII scrubbing, and background async memory."""

from __future__ import annotations

from types import SimpleNamespace

from mystery_engine.config import Settings
from mystery_engine.memory.services import (
    create_memory_service,
    create_session_service,
    drain_background_memory_tasks,
    persist_session_to_memory,
    schedule_background_memory_consolidation,
    scrub_session_for_memory,
)


async def test_sqlite_session_persists_state_across_service_restarts(tmp_path):
    db_file = tmp_path / "sessions" / "test_mystery.db"
    cfg = Settings(session_backend="sqlite", session_db_path=str(db_file))

    service_1 = create_session_service(cfg)
    created = await service_1.create_session(
        app_name="mystery_engine",
        user_id="detective_ada",
        session_id="case_001",
        state={"user:detective_rank": "Senior Detective", "discovered_clues": ["clue_1"]},
    )
    assert created.id == "case_001"
    assert db_file.exists()

    service_2 = create_session_service(cfg)
    reloaded = await service_2.get_session(
        app_name="mystery_engine",
        user_id="detective_ada",
        session_id="case_001",
    )
    assert reloaded is not None
    assert reloaded.state["discovered_clues"] == ["clue_1"]
    assert reloaded.state["user:detective_rank"] == "Senior Detective"


async def test_persist_session_to_memory_service_and_scrubs_pii():
    cfg = Settings(session_backend="memory")
    session_service = create_session_service(cfg)
    memory_service = create_memory_service(cfg)

    await session_service.create_session(
        app_name="mystery_engine",
        user_id="detective_ada",
        session_id="case_mem_1",
        state={
            "active_case": {"title": "The Midnight Horologist"},
            "player_contact": "detective@example.com / 555-234-5678",
        },
    )

    persisted = await persist_session_to_memory(
        session_service=session_service,
        memory_service=memory_service,
        app_name="mystery_engine",
        user_id="detective_ada",
        session_id="case_mem_1",
    )
    assert persisted is True

    raw = await session_service.get_session(
        app_name="mystery_engine",
        user_id="detective_ada",
        session_id="case_mem_1",
    )
    scrubbed = scrub_session_for_memory(raw)
    assert "[REDACTED_EMAIL]" in scrubbed.state["player_contact"]
    assert "[REDACTED_PHONE]" in scrubbed.state["player_contact"]

    missing = await persist_session_to_memory(
        session_service=session_service,
        memory_service=memory_service,
        app_name="mystery_engine",
        user_id="detective_ada",
        session_id="does_not_exist",
    )
    assert missing is False


async def test_background_memory_consolidation_runs_asynchronously():
    recorded = []

    class _FakeMemory:
        async def add_session_to_memory(self, session):
            recorded.append(session)

    fake_session = SimpleNamespace(
        id="bg-01",
        state={"ssn": "123-45-6789"},
        events=[],
    )
    task = schedule_background_memory_consolidation(_FakeMemory(), fake_session)
    assert not task.done()
    await drain_background_memory_tasks()
    assert task.done()
    assert len(recorded) == 1
    assert recorded[0].state["ssn"] == "[REDACTED_SSN]"
