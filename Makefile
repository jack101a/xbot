# ==============================================================================
# XBot Pro - Developer & Operator Commands
# ==============================================================================

.PHONY: help start stop restart status logs test docker-up docker-down docker-logs clean

help:
	@echo "Available commands:"
	@echo "  make start        - Start all local services (API, Worker, Dashboard, Redis)"
	@echo "  make stop         - Stop all local services"
	@echo "  make restart      - Restart all local services"
	@echo "  make status       - Inspect health and running service PIDs"
	@echo "  make logs         - Tail consolidated operational logs"
	@echo "  make test         - Run backend Pytest test suite"
	@echo "  make docker-up    - Launch multi-container stack with Docker Compose"
	@echo "  make docker-down  - Teardown Docker Compose stack"
	@echo "  make docker-logs  - View container logs across all services"
	@echo "  make clean        - Clean temporary build and python caches"

start:
	./xbot.sh start

stop:
	./xbot.sh stop

restart:
	./xbot.sh restart

status:
	./xbot.sh status

logs:
	./xbot.sh logs

test:
	cd backend && python3 -m pytest tests/

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache
