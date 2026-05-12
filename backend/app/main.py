"""
FastAPI application factory.
Wires up all routers, middleware, WebSocket (with auth), startup/shutdown hooks,
background tasks (MCP engine, stale recovery, heartbeat, Torque sync),
Prometheus metrics endpoint, and application-level rate limiting.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.devices import router as devices_router
from app.api.events import router as events_router
from app.api.jobs import router as jobs_router
from app.api.leaderboard import router as leaderboard_router
from app.api.research import router as research_router
from app.api.mcp_api import router as mcp_api_router
from app.api.stats import router as stats_router
from app.api.tasks import router as tasks_router
from app.api.campaigns import router as campaigns_router
from app.core.config import settings
from app.core.redis import close_redis, get_redis
from app.db.session import verify_db_health
from app.mcp.engine import mcp_engine
from app.services.heartbeat_service import mark_stale_devices
from app.services.leaderboard_service import recalculate_ranks
from app.services.task_service import recover_stale_tasks
from app.websocket.hub import ws_manager
from app.torque.client import torque_client
from app.core.distributed_lock import stale_recovery_lock, leaderboard_lock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

_bg_tasks: list[asyncio.Task] = []

# ── Simple in-memory metrics ──
_metrics = {
    "requests_total": 0,
    "ws_messages_total": 0,
    "tasks_assigned": 0,
    "tasks_validated": 0,
    "mcp_cycles": 0,
    "uptime_start": 0.0,
}


async def _periodic_stale_recovery() -> None:
    """Periodically recover stale tasks and mark offline devices.
    Uses distributed lock for multi-node safety."""
    from app.db.session import AsyncSessionLocal

    while True:
        try:
            acquired = await stale_recovery_lock.acquire()
            if acquired:
                try:
                    async with AsyncSessionLocal() as db:
                        await recover_stale_tasks(db)
                        await mark_stale_devices(db)
                finally:
                    await stale_recovery_lock.release()
        except Exception as e:
            logger.error(f"Stale recovery error: {e}")
        await asyncio.sleep(settings.STALE_TASK_CHECK_INTERVAL_SECONDS)


async def _periodic_leaderboard_refresh() -> None:
    """Recalculate leaderboard ranks, broadcast, and sync to Torque.
    Uses distributed lock for multi-node safety."""
    from app.db.session import AsyncSessionLocal
    from app.services.leaderboard_service import get_leaderboard as fetch_lb

    while True:
        try:
            acquired = await leaderboard_lock.acquire()
            if acquired:
                try:
                    async with AsyncSessionLocal() as db:
                        await recalculate_ranks(db)
                        entries = await fetch_lb(db, limit=20)

                        await ws_manager.broadcast("global", {
                            "type": "leaderboard_update",
                            "entries": entries,
                        })

                        if settings.TORQUE_API_KEY:
                            try:
                                await torque_client.update_leaderboard(entries)
                            except Exception as te:
                                logger.warning(f"Torque leaderboard sync failed: {te}")
                finally:
                    await leaderboard_lock.release()

        except Exception as e:
            logger.error(f"Leaderboard refresh error: {e}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    _metrics["uptime_start"] = time.time()
    db_ok = await verify_db_health()
    if db_ok:
        logger.info("Database connection verified")
        # One-time recovery: reset tasks that failed due to the 403 bug
        try:
            from app.db.session import AsyncSessionLocal
            from app.services.task_service import reset_failed_tasks
            async with AsyncSessionLocal() as db:
                await reset_failed_tasks(db)
        except Exception as e:
            logger.warning(f"Startup task reset skipped: {e}")
    else:
        logger.error("Database connection FAILED — check DATABASE_URL and Supabase status")

    await mcp_engine.start()

    _bg_tasks.append(asyncio.create_task(_periodic_stale_recovery()))
    _bg_tasks.append(asyncio.create_task(_periodic_leaderboard_refresh()))
    logger.info("Background tasks started")

    yield

    logger.info("Shutting down…")
    await mcp_engine.stop()
    for t in _bg_tasks:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
    await close_redis()
    logger.info("Shutdown complete")


# ── Simple rate limiter using Redis ──
async def _check_rate_limit(request: Request, limit: int = 60, window: int = 60) -> bool:
    """Check per-IP rate limit. Returns True if allowed."""
    try:
        redis = await get_redis()
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, window)
        return current <= limit
    except Exception:
        return True  # Fail open if Redis is down


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──
    cors_origins = settings.cors_origins_list
    allow_credentials = "*" not in cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Replay protection for sensitive endpoints ──
    from app.core.replay_protection import ReplayProtectionMiddleware
    app.add_middleware(ReplayProtectionMiddleware)

    # ── Rate limiting middleware ──
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        _metrics["requests_total"] += 1

        # Apply stricter rate limits to auth endpoints
        path = request.url.path
        if "/auth/" in path:
            allowed = await _check_rate_limit(request, limit=10, window=60)
        else:
            allowed = await _check_rate_limit(request, limit=120, window=60)

        if not allowed:
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )
        return await call_next(request)

    # ── API Routers ──
    prefix = settings.API_PREFIX
    app.include_router(auth_router, prefix=prefix)
    app.include_router(devices_router, prefix=prefix)
    app.include_router(tasks_router, prefix=prefix)
    app.include_router(jobs_router, prefix=prefix)
    app.include_router(events_router, prefix=prefix)
    app.include_router(leaderboard_router, prefix=prefix)
    app.include_router(stats_router, prefix=prefix)
    app.include_router(datasets_router, prefix=prefix)
    app.include_router(research_router, prefix=prefix)
    app.include_router(mcp_api_router, prefix=prefix)
    app.include_router(campaigns_router, prefix=prefix)

    # ── APK Download (public, no auth required) ──
    from app.api.download import router as download_router
    app.include_router(download_router, prefix=prefix)

    # ── WebSocket endpoint with JWT auth ──
    @app.websocket("/ws/{channel}")
    async def websocket_endpoint(
        websocket: WebSocket,
        channel: str = "global",
        token: str = Query(default=""),
    ):
        connected = await ws_manager.connect(websocket, channel, token or None)
        if not connected:
            return
        try:
            while True:
                data = await websocket.receive_text()
                _metrics["ws_messages_total"] += 1
        except WebSocketDisconnect:
            await ws_manager.disconnect(websocket, channel)

    # ── Health check ──
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "version": settings.VERSION,
            "ws_connections": ws_manager.connection_count,
        }

    # ── Prometheus-compatible metrics ──
    @app.get("/metrics")
    async def metrics():
        uptime = time.time() - _metrics["uptime_start"] if _metrics["uptime_start"] else 0
        lines = [
            f'# HELP desci_requests_total Total HTTP requests',
            f'# TYPE desci_requests_total counter',
            f'desci_requests_total {_metrics["requests_total"]}',
            f'# HELP desci_ws_connections Current WebSocket connections',
            f'# TYPE desci_ws_connections gauge',
            f'desci_ws_connections {ws_manager.connection_count}',
            f'# HELP desci_uptime_seconds Uptime in seconds',
            f'# TYPE desci_uptime_seconds gauge',
            f'desci_uptime_seconds {uptime:.0f}',
        ]
        return Response(
            content="\n".join(lines) + "\n",
            media_type="text/plain",
        )

    return app


app = create_app()
