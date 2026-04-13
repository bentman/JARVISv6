from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import datetime
import threading
import traceback

from fastapi import FastAPI

from backend.app.api.dependencies import get_startup_context, set_startup_error
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.session import router as session_router

_LOG = Path(__file__).resolve().parents[4] / "reports" / "backend_startup.log"


def _log(msg: str) -> None:
    _LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")
        f.flush()


def _warm_startup_context() -> None:
    _log("warm thread started")
    try:
        get_startup_context()
        _log("warm thread completed OK")
    except Exception as exc:
        msg = f"warm thread FAILED: {exc}\n{traceback.format_exc()}"
        _log(msg)
        set_startup_error(str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log("lifespan: starting warm thread")
    t = threading.Thread(target=_warm_startup_context, daemon=True, name="startup-context-warm")
    t.start()
    yield
    _log("lifespan: server shutting down")


app = FastAPI(title="JARVISv6 Backend API", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(session_router)
