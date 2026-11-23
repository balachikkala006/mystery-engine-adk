"""Session persistence, PII scrubbing, and background async memory consolidation.

Supports:
- Persistent SQLite sessions (`SqliteSessionService` / `DatabaseSessionService`) for
  multi-turn restarts, or `InMemorySessionService` for isolated unit tests.
- Long-term `MemoryService` (`VertexAiMemoryBankService` in Google Cloud or
  `InMemoryMemoryService` locally).
- Active PII scrubbing before any session snapshot is stored into long-term memory.
- Non-blocking background async consolidation (`schedule_background_memory_consolidation`)
  using `asyncio.create_task` so expensive memory generation never stalls user turns.
"""

from __future__ import annotations

import asyncio
import copy
import logging
from typing import Any

from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService

from mystery_engine.config import Settings, get_settings
from mystery_engine.observability.pii_redaction import redact_pii, redact_structure

logger = logging.getLogger(__name__)

# Active background memory consolidation tasks tracked to avoid GC leaks & allow clean drain.
_BACKGROUND_MEMORY_TASKS: set[asyncio.Task[Any]] = set()


def create_session_service(settings: Settings | None = None) -> Any:
    """Create the configured ADK SessionService."""
    cfg = settings or get_settings()
    if cfg.session_backend == "memory":
        logger.info("Using InMemorySessionService for ephemeral session storage.")
        return InMemorySessionService()

    db_path = cfg.ensure_data_dirs()
    try:
        from google.adk.sessions.sqlite_session_service import SqliteSessionService

        logger.info("Using SqliteSessionService backed by %s", db_path)
        return SqliteSessionService(db_path=str(db_path))
    except ImportError:
        try:
            from google.adk.sessions import DatabaseSessionService

            db_url = f"sqlite+aiosqlite:///{db_path.resolve()}"
            logger.info("Using DatabaseSessionService backed by %s", db_url)
            return DatabaseSessionService(db_url=db_url)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("SQLite session service unavailable (%s); using in-memory.", exc)
            return InMemorySessionService()


def create_memory_service(settings: Settings | None = None) -> Any:
    """Create the configured ADK long-term MemoryService."""
    cfg = settings or get_settings()
    if cfg.agent_engine_id and cfg.gcp_project:
        try:
            from google.adk.memory import VertexAiMemoryBankService

            logger.info(
                "Using VertexAiMemoryBankService (project=%s, agent_engine_id=%s)",
                cfg.gcp_project,
                cfg.agent_engine_id,
            )
            return VertexAiMemoryBankService(
                project=cfg.gcp_project,
                location=cfg.gcp_location,
                agent_engine_id=cfg.agent_engine_id,
            )
        except Exception as exc:  # pragma: no cover - optional cloud dep
            logger.warning(
                "VertexAiMemoryBankService unavailable (%s); using InMemoryMemoryService.",
                exc,
            )

    logger.info("Using InMemoryMemoryService for cross-session detective memory.")
    return InMemoryMemoryService()


def scrub_session_for_memory(session: Any) -> Any:
    """Return a PII-scrubbed copy of a session before archiving to long-term MemoryService."""
    try:
        sanitized = copy.deepcopy(session)
    except Exception:
        sanitized = session

    if isinstance(getattr(sanitized, "state", None), dict):
        sanitized.state = redact_structure(sanitized.state)

    events = getattr(sanitized, "events", None) or []
    for event in events:
        content = getattr(event, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            text = getattr(part, "text", None)
            if isinstance(text, str) and text:
                part.text = redact_pii(text)
    return sanitized


async def persist_session_to_memory(
    session_service: Any,
    memory_service: Any,
    app_name: str,
    user_id: str,
    session_id: str,
) -> bool:
    """Fetch a session, scrub PII, and persist it into the long-term MemoryService."""
    session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        logger.warning("Cannot persist memory: session '%s' not found.", session_id)
        return False

    sanitized_session = scrub_session_for_memory(session)
    await memory_service.add_session_to_memory(sanitized_session)
    logger.info(
        "Persisted PII-scrubbed session '%s' for user '%s' into long-term memory.",
        session_id,
        user_id,
    )
    return True


def schedule_background_memory_consolidation(
    memory_service: Any,
    session: Any,
    *,
    session_id: str | None = None,
) -> asyncio.Task[bool]:
    """Schedule PII-scrubbed memory consolidation as a non-blocking background asyncio task.

    Prevents expensive memory generation or remote Memory Bank writes from blocking the
    interactive chat turn.
    """
    resolved_id = session_id or getattr(session, "id", "unknown")

    async def _consolidate() -> bool:
        try:
            sanitized = scrub_session_for_memory(session)
            await memory_service.add_session_to_memory(sanitized)
            logger.info(
                "Background memory consolidation completed for session '%s'.",
                resolved_id,
                extra={"extra_fields": {"event": "memory_consolidated", "session_id": resolved_id}},
            )
            return True
        except Exception as exc:  # pragma: no cover - defensive background handler
            logger.warning(
                "Background memory consolidation failed for session '%s': %s",
                resolved_id,
                exc,
            )
            return False

    task = asyncio.create_task(_consolidate(), name=f"memory-consolidate-{resolved_id}")
    _BACKGROUND_MEMORY_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_MEMORY_TASKS.discard)
    return task


async def drain_background_memory_tasks() -> int:
    """Await all currently scheduled background memory tasks (for clean shutdown/tests)."""
    pending = list(_BACKGROUND_MEMORY_TASKS)
    if not pending:
        return 0
    await asyncio.gather(*pending, return_exceptions=True)
    return len(pending)
