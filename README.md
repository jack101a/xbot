# XBot Pro: Autonomous Agent Platform for X

XBot Pro is a production-ready, autonomous AI agent platform engineered for high-impact social media management on X. Featuring an asynchronous modular architecture, dynamic circadian scheduling, multi-tier LLM reasoning, computer vision / image synthesis, anti-hallucination memory synthesis, and a modern glassmorphic dashboard.

---

## ⚡ Quick Start: Docker Deployment (Recommended)

XBot is fully containerized and multi-architecture ready (`linux/amd64` and `linux/arm64`). Docker images are automatically built and published to GitHub Container Registry (GHCR).

### 1. Clone & Configure Environment
```bash
git clone https://github.com/jack101a/xbot.git
cd xbot

# Copy example environment configuration
cp .env.example .env

# Edit .env with your LiteLLM API base URL, keys, and credentials
nano .env
```

### 2. Launch Services with Docker Compose
```bash
# Pull and start all services (Redis, Backend API, Celery Worker, Next.js Dashboard)
docker compose up -d
```

### 3. Access Dashboard & API
- **Admin Dashboard**: `http://localhost:3002`
- **FastAPI Documentation**: `http://localhost:8200/docs`
- **Health Check**: `http://localhost:8200/api/health`

### 4. Stop Services
```bash
docker compose down
```

---

## 💻 Bare-Metal / Local Development Setup

If running directly on Linux/macOS host:

### Prerequisites
- Python 3.11+
- Node.js 20+ & npm
- Redis server (`redis-server`)

### Launch All Services
We provide a unified orchestrator script `xbot.sh`:

```bash
# Start Redis, FastAPI backend, Celery worker + beat, and Next.js dashboard
./xbot.sh start

# Check operational status of all services
./xbot.sh status

# View live consolidated logs
./xbot.sh logs

# Restart or stop services
./xbot.sh restart
./xbot.sh stop
```

---

## 🏗 Architecture & Core Components

```
xbot/
├── .github/workflows/         # CI/CD: Automated multi-arch GHCR image builds
│   └── docker.yml
├── backend/                   # FastAPI REST API & Core Engine
│   ├── pyproject.toml         # Dependency definitions (FastAPI, Celery, Playwright)
│   ├── alembic.ini            # Database schema migrations
│   ├── xbot/
│   │   ├── ai/                # LLM cascades, prompt engine, topic radar, reflection
│   │   ├── api/               # REST API endpoints (profiles, campaigns, system)
│   │   ├── browser/           # Playwright stealth driver and humanized actions
│   │   ├── contracts/         # Domain ports & DTO contracts (Hexagonal Architecture)
│   │   ├── growth/            # Follow-for-follow and community harvesting engine
│   │   ├── infra/             # Adapter implementations (browser queue, LLM bridges)
│   │   ├── models/            # SQLAlchemy database ORM models
│   │   ├── persona/           # Character cards, worldview engine, memory/diary
│   │   ├── pipelines/         # High-level pipelines (quote, reply, instant trend)
│   │   ├── safety/            # Circuit breakers, rate limits, topic blacklists
│   │   ├── scheduling/        # Circadian rhythms and natural active window calculations
│   │   └── tasks/             # Celery asynchronous task definitions & session loops
│   └── tests/                 # Full test suite (Pytest + Asyncio)
├── dashboard/                 # Next.js 16 Web Dashboard (Control Center)
│   ├── src/app/               # App Router pages and responsive layout
│   ├── src/features/          # Persona studio, Growth engine, Campaign studio, Pruner
│   └── src/store/             # Zustand state management
├── data/                      # Local volume mount for persistent profiles, DB, and media
├── docker/                    # Container Dockerfiles
│   ├── Dockerfile.api         # Lightweight Python 3.11 slim backend image
│   └── Dockerfile.worker      # Playwright + Celery worker image (Dual AMD64/ARM64)
├── docker-compose.yml         # Multi-service stack definition
├── xbot.sh                    # Unified service CLI manager
└── README.md
```

---

## 🚢 CI/CD & Container Registry (GHCR)

The repository includes a GitHub Actions workflow (`.github/workflows/docker.yml`) that triggers on every push to `main` and version tags:

- **Build Matrix**: Concurrently compiles `xbot-api`, `xbot-worker`, and `xbot-dashboard`.
- **Architectures**: Dual-target cross-compilation for `linux/amd64` and `linux/arm64` via Docker Buildx & QEMU.
- **Images Published**:
  - `ghcr.io/jack101a/xbot-api:latest`
  - `ghcr.io/jack101a/xbot-worker:latest`
  - `ghcr.io/jack101a/xbot-dashboard:latest`

---

## 🔒 Security & Best Practices

- **Never Commit Secrets**: Live credentials, session cookies (`storage_state.json`), and API keys in `.env` are strictly excluded in `.gitignore` and `.dockerignore`.
- **Rate Limits & Circuit Breakers**: Built-in sliding window rate limiters and autonomous cool-down algorithms protect accounts against platform detection.
- **Database Safety**: SQLite with async WAL mode enabled, or point to external PostgreSQL with zero code changes.
