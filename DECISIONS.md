# Decisions: XBot

## 2026-06-18: Initial Architecture Mapping

### DEC-001: Backend Framework Choice
- **Decision:** Python 3.12+ with FastAPI, Celery, and Playwright.
- **Rationale:** Playwright and Celery have mature and robust ecosystems in Python, and FastAPI provides high-performance asynchronous endpoints with auto-documentation.
- **Implications:** The entire backend code will reside in a python environment under `backend/`.

### DEC-002: Project Init using `uv`
- **Decision:** We use standard python tooling with `uv` for lightning-fast package management and dependency pinning.
- **Rationale:** `uv` is significantly faster than standard `pip` or `poetry` and creates reproducible environments.
- **Implications:** A `pyproject.toml` and lock files will be generated in `backend/`.

### DEC-003: Strict Linting and Type Checking Configuration
- **Decision:** Enable `mypy` strict mode and configure a comprehensive set of `ruff` rules (such as Pyupgrade, Bugbear, Simplicity, etc.) with a target line length of 88.
- **Rationale:** Ensures clean code formatting, avoids deprecated constructs, and guarantees full type safety early on.
- **Implications:** All backend files and tests must satisfy these static checks.

### DEC-004: Rename Virtual Environment to `.venv`
- **Decision:** Renamed the Python virtual environment folder from `venv` to `.venv`.
- **Rationale:** `uv` detects the `.venv` directory automatically, removing the need to specify the path explicitly in commands.
- **Implications:** The local virtual environment resides in `backend/.venv`.

### DEC-005: Switch Database from PostgreSQL to SQLite
- **Decision:** Switch to SQLite using the `aiosqlite` asynchronous driver for SQLAlchemy instead of PostgreSQL.
- **Rationale:** Simplifies setup, avoids managing a heavy Postgres service, and fits the scale of a single-user system in its initial phase.
- **Implications:** The database URL is configured to `sqlite+aiosqlite:///.../xbot.db`.

### DEC-006: Utilize Host Native Redis and External LiteLLM
- **Decision:** Connect to the existing native Redis instance on localhost:6379 and use the pre-running LiteLLM proxy on the VPS.
- **Rationale:** Reduces container resource consumption and avoids port binding conflicts, while speeding up the startup phase.
- **Implications:** We do not spin up local Docker containers for Redis or LiteLLM in the development stack.

### DEC-007: Enable Modern Python Deferred Type Annotations in Database Models
- **Decision:** Added `from __future__ import annotations` at the top of all model files.
- **Rationale:** Allows PEP 604 type unions (like `ActionResult | None`) with forward string annotations (used for model relationships) without throwing a runtime `TypeError` on Python 3.11.
- **Implications:** All modern typing operations evaluate properly during type resolution.

### DEC-008: Configure Alembic Async Migrations and Symlink `.env`
- **Decision:** Customized the Alembic environment (`migrations/env.py`) to run online migrations in an asynchronous event loop via `create_async_engine`, and created a symbolic link from the root `.env` to `backend/.env`.
- **Rationale:** Ensures the database migrations share the same settings source of truth and correctly execute async operations required by the `aiosqlite` driver.
- **Implications:** DB updates can be generated and applied with standard Alembic commands.

### DEC-009: Implement Profile CRUD API Endpoints and SQLite Test Database isolation
- **Decision:** Designed standard RESTful routes (`/api/profiles`) with fully-async DB operations using SQLAlchemy 2.0 query patterns. For integration testing, configured a custom pytest fixture to override the database dependency to a temporary `test_temp.db` database.
- **Rationale:** Keeps production data separated from tests while checking real database updates and schema constraints.
- **Implications:** Endpoints are fully functional and verifiable.

### DEC-010: Implement Persona Loader and JSONL Memory/Diary Storage
- **Decision:** Built a typed YAML loader using `ruamel.yaml` and Pydantic models for identity/operational/strategy configs. Implemented a daily diary writer and a JSONL-based memory system that retrieves memories via a priority pipeline (recency + importance >= 0.8 + query matching) and caps it using token estimation.
- **Rationale:** Separates static character configurations (soul) from operational settings and dynamic context, maintaining safety limits and token conservation.
- **Implications:** The AI brain can cleanly load profile contexts and episodic memories.

### DEC-011: Local Mock X Server for Browser Automation
- **Decision:** Implemented a lightweight mock X (Twitter) server using FastAPI, serving raw HTML pages mimicking the main X selectors (tweets, sidebar post, compose modals, profiles, and follow button clicks).
- **Rationale:** Allows local execution of the browser action library without hitting rate limits, CAPTCHAs, or risking accounts.
- **Implications:** Automation flow is testable locally and deterministically.

### DEC-012: Custom Routing Interception with HTTPX
- **Decision:** Configured a custom Playwright request routing interceptor in integration tests that uses python-side `httpx.AsyncClient` to retrieve mock content and fulfill requests natively.
- **Rationale:** Cross-protocol redirects (redirecting `https://x.com` to `http://localhost`) are natively blocked by Playwright's `Route.continue_(url=...)` mechanism. Fulfilling the route directly with local content resolves this restriction.
- **Implications:** Absolute URL actions (`https://x.com/...`) are successfully emulated locally.

### DEC-013: Native Development and Testing on Localhost
- **Decision:** Portainer stack and Docker-compose configurations are bypassed for local testing, running the Redis broker, SQLite database, FastAPI backend, and mock servers natively.
- **Rationale:** Aligns with developer constraints to keep the development stack resource-light and easily debuggable during initial phases.
- **Implications:** Docker is not required for testing.
