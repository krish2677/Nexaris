# DeSci Compute Network

> Decentralized Compute Platform with MCP-Driven Incentive Orchestration & Torque Protocol Integration

A production-grade decentralized compute platform where users contribute idle compute power from Android devices. The system distributes computational workloads as verifiable work units, validates results through duplicate execution, dynamically adjusts incentives using an MCP engine, and integrates with Torque Protocol for leaderboards, rewards, and retention campaigns.

## Architecture

```
[ Android App ]
       ↓
 FastAPI Backend  ←→  Supabase PostgreSQL
       ↓
  Task Queue (Redis)
       ↓
  MCP Rule Engine
       ↓
 Torque Integration
```

## Project Structure

```
DeSci/
├── backend/           # FastAPI + PostgreSQL + Redis
│   ├── app/
│   │   ├── api/       # REST endpoints (auth, tasks, jobs, events, stats)
│   │   ├── core/      # Config, security, Redis, Supabase storage
│   │   ├── db/        # SQLAlchemy async session + base
│   │   ├── models/    # 7 database models
│   │   ├── schemas/   # Pydantic request/response schemas
│   │   ├── services/  # Business logic (auth, tasks, validation, heartbeat)
│   │   ├── workers/   # Compute templates (Monte Carlo, Stats, Matrix)
│   │   ├── mcp/       # MCP incentive rule engine
│   │   ├── torque/    # Torque Protocol client
│   │   └── websocket/ # Real-time broadcast hub
│   ├── alembic/       # Database migrations
│   ├── tests/         # Pytest test suite
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── android/           # Kotlin + Jetpack Compose + Hilt
│   └── app/src/main/java/com/desci/compute/
│       ├── compute/   # ComputeService, templates, health checks
│       ├── data/      # API service, Room DB, token store
│       ├── di/        # Hilt dependency injection
│       └── ui/        # Compose screens, ViewModels, navigation
│
└── dashboard/         # React + TypeScript (Vite)
    └── src/
        ├── pages/     # Overview, Jobs, Leaderboard, MCP Dashboard
        ├── api.ts     # Typed API client
        └── App.tsx    # Sidebar navigation + auth gate
```

## Supported Compute Templates

| Template | Description | Inputs | Validation |
|----------|------------|--------|------------|
| Monte Carlo | Pi estimation via SHA-256 seeded points | seed, range | Deterministic |
| Dataset Stats | Multi-column aggregation (sum, avg, variance) | seed, columns, rows | Deterministic |
| Matrix Compute | Block matrix multiplication | seed, matrix_size | Deterministic |

All templates are **fully deterministic** — same inputs always produce identical outputs, enabling trustless verification.

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
# Set your Supabase credentials in .env
# CORS_ORIGINS is set to * by default for development
# If you use PgBouncer, statement_cache_size is disabled in app/db/session.py
uvicorn app.main:app --reload
```  

### Dashboard
```bash
cd dashboard
npm install
npm run dev
```

### Android (Emulator)
- If you connect to the backend via 10.0.2.2, cleartext HTTP is enabled in the manifest.

### Docker
```bash
cd backend
docker-compose up --build
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Login, get JWT |
| POST | `/api/v1/devices/register` | Register compute device |
| POST | `/api/v1/devices/heartbeat` | Update device liveness |
| GET | `/api/v1/tasks/task` | Request task assignment |
| POST | `/api/v1/tasks/submit` | Submit computed result |
| POST | `/api/v1/jobs/` | Create a compute job |
| GET | `/api/v1/jobs/` | List jobs |
| GET | `/api/v1/leaderboard/` | Get contributor ranking |
| GET | `/api/v1/stats/` | Platform-wide metrics |
| POST | `/api/v1/events/` | Emit custom event |
| WS | `/ws/{channel}` | Real-time updates |

## MCP Engine Rules

1. **Worker Shortage Detection** — Auto-boosts `reward_multiplier` when `active_workers < required_workers`
2. **Inactive User Re-engagement** — Emits events after 24h inactivity
3. **Contribution Scoring** — `score = validated_units × device_power_factor × urgency_multiplier`

## Security

- JWT Bearer authentication on all protected endpoints
- Nginx rate limiting (30r/s API, 5r/s auth)
- HMAC-SHA256 task signature validation
- Encrypted token storage on Android (DataStore)
- CORS configuration
- ProGuard obfuscation for release builds

Note: CORS is set to allow all origins by default for development. Lock this down for production.

## Environment Variables

Copy `.env.example` to `.env` and fill in:
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase PostgreSQL async connection string |
| `SYNC_DATABASE_URL` | Supabase PostgreSQL sync connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `REDIS_URL` | Redis connection URL |
| `SECRET_KEY` | JWT signing secret |
| `TORQUE_API_KEY` | Torque Protocol API key |
| `CORS_ORIGINS` | Comma-separated origins or `*` to allow all |

## License

MIT
