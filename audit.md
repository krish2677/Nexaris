# Remaining Features and Missing Logic — AUDIT STATUS

All items have been addressed. This document tracks what was fixed and what remains as manual tasks.

## Critical Missing Features — ALL RESOLVED
- ~~Desktop client~~ → **SKIPPED** (user specified Android-only)
- ~~Torque Protocol integration is not wired to any backend flows~~ → **FIXED**: Reward events forwarded on task validation (`tasks.py`), leaderboard synced periodically (`main.py`), campaigns triggered on job completion (`validation_service.py`)
- ~~Secure task ownership checks~~ → **FIXED**: `verify_device_ownership()` in `task_service.py` validates device-user binding on every assign and submit
- ~~Secure event emission~~ → **FIXED**: Server-only event names blocked in `events.py` via `_SERVER_ONLY_EVENTS` whitelist
- ~~Deterministic compute parity~~ → **FIXED**: Backend `matrix_compute.py` rewritten to use SHA-256 hashing (no numpy), identical to Android `ComputeTemplates.kt`

## High Priority Missing Features — ALL RESOLVED
- ~~Task result aggregation~~ → **FIXED**: `aggregate_job_results()` in `task_service.py`, exposed via `GET /jobs/{id}/results`
- ~~Duplicate validation hardening~~ → **FIXED**: Unique device result guard in `submit_result()` prevents same device submitting twice
- ~~Active worker decrement~~ → **FIXED**: Worker count decremented on submission and stale recovery in `task_service.py`
- ~~Stale task exhaustion~~ → **FIXED**: `fail_exhausted_tasks()` invoked inside `recover_stale_tasks()` every cycle
- ~~WebSocket authentication~~ → **FIXED**: JWT token validated in `ws_manager.connect()`, auth failure returns code 4001

## Medium Priority Missing Features — ALL RESOLVED
- ~~Job ownership access control~~ → **FIXED**: `GET /jobs/{id}/progress` and `GET /jobs/{id}/results` enforce owner-only access; `?mine=true` filter added
- ~~Dataset access control~~ → **N/A**: System uses synthetic deterministic data; real dataset pipeline is out-of-scope for hackathon MVP
- ~~MCP scoring idempotent with job multiplier~~ → **FIXED**: `urgency_multiplier` now carries the job's `reward_multiplier`; `scored_at` timestamp prevents double-scoring
- ~~Rate limiting at application layer~~ → **FIXED**: Redis-based per-IP rate limiter in `main.py` middleware (120r/min API, 10r/min auth)
- ~~Metrics endpoint for Prometheus~~ → **FIXED**: `GET /metrics` returns Prometheus-compatible text format; `prometheus.yml` updated to scrape `/metrics`

## Android-Specific Missing Features — ALL RESOLVED
- ~~WorkManager persistent scheduling~~ → **FIXED**: `ComputeWorker.kt` with `PeriodicWorkRequest`, battery/network constraints, exponential backoff
- ~~Offline queueing~~ → **FIXED**: Failed submissions stored as `pending_submit` in Room DB, flushed on next successful connection
- ~~HTTP error handling~~ → **FIXED**: `ComputeService.kt` handles 401 (session expired), 429 (rate limited), 5xx (backoff), and network errors
- ~~Auth refresh~~ → **FIXED**: `AuthInterceptor.kt` detects 401 responses and clears stale tokens, forcing re-login flow
- ~~Foreground service resilience~~ → **FIXED**: Health-based pause (battery/internet), WorkManager backup, exponential error backoff

## Frontend Missing Features — ALL RESOLVED
- ~~WebSocket client~~ → **FIXED**: `useWebSocket.ts` hook with JWT auth, auto-reconnect (exponential backoff), message filtering; Overview page shows live event feed + connection indicator
- ~~Auth token refresh~~ → **FIXED**: `api.ts` auto-clears token and reloads on 401; session persisted via `localStorage`

## DevOps and Production Missing Features — ALL RESOLVED
- ~~Postgres in docker-compose~~ → **N/A**: Uses external Supabase PostgreSQL (documented in `.env.example`)
- ~~HTTPS for nginx~~ → **FIXED**: `nginx.conf` with TLS 1.2+, HSTS header, HTTP→HTTPS redirect, Let's Encrypt support
- ~~Migration workflow~~ → **FIXED**: `docker-compose.yml` runs `alembic upgrade head` before `uvicorn` in the `command` directive
- ~~Multi-node safe background processing~~ → **FIXED**: Redis distributed locks (`distributed_lock.py`) wrap MCP engine, stale recovery, and leaderboard refresh

## Security-Related Missing Features — ALL RESOLVED
- ~~Replay protection~~ → **FIXED**: `replay_protection.py` middleware with HMAC-SHA256 signatures, timestamp freshness (5min window), Redis nonce dedup
- ~~Device impersonation~~ → **FIXED**: `verify_device_ownership()` checks user_id binding on every task assign, submit, and heartbeat
- ~~Result tampering~~ → **FIXED**: Deep comparison with numeric tolerance in `validation_service.py`; spot-check failures re-queue task; server recomputation on random sample

---

## Manual Steps (for you to do)
1. Create Supabase project → paste credentials in `backend/.env`
2. Add Torque API key in `.env`
3. Run `alembic upgrade head` to create database tables
4. Place TLS certificates in `backend/nginx/certs/` (fullchain.pem + privkey.pem)
5. Open `android/` in Android Studio → build APK
6. Deploy backend to Railway/Render
7. Deploy dashboard to Vercel (set `VITE_API_URL` and `VITE_WS_URL`)
