#!/usr/bin/env bash
# ==============================================================================
# XBot Pro: Unified Service Manager (Start, Stop, Restart, Status, Logs)
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
DASHBOARD_DIR="${PROJECT_ROOT}/dashboard"
PID_DIR="${PROJECT_ROOT}/.pids"
LOG_DIR="${PROJECT_ROOT}/logs"

VENV_PYTHON="${BACKEND_DIR}/.venv/bin/python"
VENV_CELERY="${BACKEND_DIR}/.venv/bin/celery"

mkdir -p "${PID_DIR}" "${LOG_DIR}"

BACKEND_PORT="${LOCAL_API_PORT:-8200}"
DASHBOARD_PORT="${LOCAL_DASHBOARD_PORT:-3002}"
ALT_BACKEND_PORT="${ALT_API_PORT:-8300}"
ALT_DASHBOARD_PORT="${ALT_DASH_PORT:-3003}"

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

is_port_in_use() {
    local port=$1
    if ss -tulpn 2>/dev/null | grep -q ":${port} "; then
        return 0
    elif netstat -tulpn 2>/dev/null | grep -q ":${port} "; then
        return 0
    elif lsof -i ":${port}" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

is_pid_running() {
    local pid_file=$1
    if [ -f "${pid_file}" ]; then
        local pid
        pid=$(cat "${pid_file}")
        if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

ensure_redis() {
    if ! command -v redis-cli >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️ redis-cli not found, skipping redis ping check.${NC}"
        return 0
    fi

    if ! redis-cli ping >/dev/null 2>&1; then
        echo -e "${YELLOW}🔄 Redis server is not running. Starting redis-server...${NC}"
        sudo systemctl start redis-server 2>/dev/null || redis-server --daemonize yes 2>/dev/null || true
        sleep 1
        if redis-cli ping >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Redis server started successfully.${NC}"
        else
            echo -e "${RED}❌ Failed to start Redis. Please start redis manually.${NC}"
        fi
    fi
}

start_services() {
    echo -e "\n${BOLD}${CYAN}======================================================${NC}"
    echo -e "${BOLD}${CYAN}          🚀 Starting XBot Pro Services               ${NC}"
    echo -e "${BOLD}${CYAN}======================================================${NC}\n"

    ensure_redis

    # 1. Start FastAPI Backend (Port ${BACKEND_PORT})
    if is_pid_running "${PID_DIR}/backend.pid" || is_port_in_use "${BACKEND_PORT}"; then
        echo -e "${YELLOW}⚡ FastAPI Backend is already running on port ${BACKEND_PORT}.${NC}"
    else
        echo -n "Starting FastAPI Backend (port ${BACKEND_PORT})... "
        cd "${BACKEND_DIR}"
        setsid "${VENV_PYTHON}" -m uvicorn xbot.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" </dev/null > "${LOG_DIR}/backend.log" 2>&1 &
        echo $! > "${PID_DIR}/backend.pid"
        cd "${PROJECT_ROOT}"
        sleep 2
        if is_pid_running "${PID_DIR}/backend.pid" || is_port_in_use "${BACKEND_PORT}"; then
            echo -e "${GREEN}DONE (PID: $(cat "${PID_DIR}/backend.pid"))${NC}"
        else
            echo -e "${RED}FAILED${NC} (Check logs/backend.log)"
        fi
    fi

    # 2. Start Celery Task Worker with Beat (bounded concurrency=1, queue=celery)
    if is_pid_running "${PID_DIR}/celery.pid"; then
        echo -e "${YELLOW}⚡ Celery Task Worker & Beat is already running.${NC}"
    else
        echo -n "Starting Celery Task Worker & Beat (concurrency=3, queue=publish,celery)... "
        cd "${BACKEND_DIR}"
        setsid "${VENV_CELERY}" -A xbot.celery_app worker --beat -Q publish,celery --concurrency=3 -n tasks@%h --loglevel=info </dev/null > "${LOG_DIR}/celery.log" 2>&1 &
        echo $! > "${PID_DIR}/celery.pid"
        cd "${PROJECT_ROOT}"
        sleep 2
        if is_pid_running "${PID_DIR}/celery.pid"; then
            echo -e "${GREEN}DONE (PID: $(cat "${PID_DIR}/celery.pid"))${NC}"
        else
            echo -e "${RED}FAILED${NC} (Check logs/celery.log)"
        fi
    fi

    # 3. Start Dedicated Celery Browser Worker (bounded concurrency=1, queue=browser)
    if is_pid_running "${PID_DIR}/celery_browser.pid"; then
        echo -e "${YELLOW}⚡ Celery Browser Worker is already running.${NC}"
    else
        echo -n "Starting Celery Browser Action Worker (concurrency=1, queue=browser)... "
        cd "${BACKEND_DIR}"
        setsid "${VENV_CELERY}" -A xbot.celery_app worker -Q browser --concurrency=1 -n browser@%h --loglevel=info </dev/null > "${LOG_DIR}/celery_browser.log" 2>&1 &
        echo $! > "${PID_DIR}/celery_browser.pid"
        cd "${PROJECT_ROOT}"
        sleep 2
        if is_pid_running "${PID_DIR}/celery_browser.pid"; then
            echo -e "${GREEN}DONE (PID: $(cat "${PID_DIR}/celery_browser.pid"))${NC}"
        else
            echo -e "${RED}FAILED${NC} (Check logs/celery_browser.log)"
        fi
    fi

    # 3. Start Dashboard UI (Port ${DASHBOARD_PORT} - Production Static SPA Mode to prevent memory bloat)
    if is_pid_running "${PID_DIR}/dashboard.pid" || is_port_in_use "${DASHBOARD_PORT}"; then
        echo -e "${YELLOW}⚡ Dashboard UI is already running on port ${DASHBOARD_PORT}.${NC}"
    else
        echo -n "Starting Dashboard UI (port ${DASHBOARD_PORT}, lightweight production mode)... "
        cd "${DASHBOARD_DIR}"
        if [ -d "${DASHBOARD_DIR}/out" ]; then
            setsid npx --yes serve -s "${DASHBOARD_DIR}/out" -l "${DASHBOARD_PORT}" -p "${DASHBOARD_PORT}" </dev/null > "${LOG_DIR}/dashboard.log" 2>&1 &
        else
            setsid npx next dev -p "${DASHBOARD_PORT}" -H 0.0.0.0 </dev/null > "${LOG_DIR}/dashboard.log" 2>&1 &
        fi
        echo $! > "${PID_DIR}/dashboard.pid"
        cd "${PROJECT_ROOT}"
        sleep 2
        if is_pid_running "${PID_DIR}/dashboard.pid" || is_port_in_use "${DASHBOARD_PORT}"; then
            echo -e "${GREEN}DONE (PID: $(cat "${PID_DIR}/dashboard.pid"))${NC}"
        else
            echo -e "${RED}FAILED${NC} (Check logs/dashboard.log)"
        fi
    fi

    # 4. Start Resource Telemetry Recorder (every 5 minutes / 300s, zero-bloat capped)
    if is_pid_running "${PID_DIR}/monitor.pid"; then
        echo -e "${YELLOW}⚡ Resource Telemetry Recorder is already running.${NC}"
    else
        echo -n "Starting Resource Telemetry Recorder (5m interval, zero-bloat)... "
        setsid "${VENV_PYTHON}" "${PROJECT_ROOT}/scripts/resource_monitor.py" --record --interval 300 </dev/null > "${LOG_DIR}/monitor.log" 2>&1 &
        echo $! > "${PID_DIR}/monitor.pid"
        sleep 1
        if is_pid_running "${PID_DIR}/monitor.pid"; then
            echo -e "${GREEN}DONE (PID: $(cat "${PID_DIR}/monitor.pid"))${NC}"
        else
            echo -e "${RED}FAILED${NC} (Check logs/monitor.log)"
        fi
    fi

    # Optional dual-port listener (forward 8300->8200 and 3003->3002 so both port pairs work seamlessly)
    if command -v socat >/dev/null 2>&1; then
        if ! is_port_in_use "${ALT_BACKEND_PORT}"; then
            setsid socat TCP-LISTEN:${ALT_BACKEND_PORT},fork,reuseaddr TCP:127.0.0.1:${BACKEND_PORT} </dev/null >/dev/null 2>&1 &
        fi
        if ! is_port_in_use "${ALT_DASHBOARD_PORT}"; then
            setsid socat TCP-LISTEN:${ALT_DASHBOARD_PORT},fork,reuseaddr TCP:127.0.0.1:${DASHBOARD_PORT} </dev/null >/dev/null 2>&1 &
        fi
    fi

    echo -e "\n${BOLD}${GREEN}======================================================${NC}"
    echo -e "${BOLD}${GREEN}            🎉 All Services Active!                   ${NC}"
    echo -e "${BOLD}${GREEN}======================================================${NC}"
    echo -e "  🌐 ${BOLD}Dashboard UI (Local):${NC}    ${CYAN}http://localhost:${DASHBOARD_PORT}${NC} (also: http://localhost:${ALT_DASHBOARD_PORT})"
    echo -e "  🔌 ${BOLD}Backend API (Local):${NC}     ${CYAN}http://localhost:${BACKEND_PORT}${NC} (also: http://localhost:${ALT_BACKEND_PORT})"
    echo -e "  📖 ${BOLD}API Docs (Local):${NC}        ${CYAN}http://localhost:${BACKEND_PORT}/docs${NC}"
    echo -e "  📂 ${BOLD}Log Directory:${NC}          ${YELLOW}${LOG_DIR}/${NC}\n"
}

stop_services() {
    echo -e "\n${BOLD}${RED}======================================================${NC}"
    echo -e "${BOLD}${RED}          🛑 Stopping XBot Pro Services               ${NC}"
    echo -e "${BOLD}${RED}======================================================${NC}\n"

    # 1. Stop Dashboard PID
    if [ -f "${PID_DIR}/dashboard.pid" ]; then
        local pid
        pid=$(cat "${PID_DIR}/dashboard.pid")
        if kill -0 "${pid}" 2>/dev/null; then
            echo -n "Stopping Dashboard UI (PID: ${pid})... "
            kill -15 "${pid}" 2>/dev/null || true
            sleep 1
            if kill -0 "${pid}" 2>/dev/null; then
                kill -9 "${pid}" 2>/dev/null || true
            fi
            echo -e "${GREEN}STOPPED${NC}"
        fi
        rm -f "${PID_DIR}/dashboard.pid"
    fi

    # 2. Stop Celery Task PID
    if [ -f "${PID_DIR}/celery.pid" ]; then
        local pid
        pid=$(cat "${PID_DIR}/celery.pid")
        if kill -0 "${pid}" 2>/dev/null; then
            echo -n "Stopping Celery Task Worker & Beat (PID: ${pid})... "
            kill -15 "${pid}" 2>/dev/null || true
            sleep 1
            if kill -0 "${pid}" 2>/dev/null; then
                kill -9 "${pid}" 2>/dev/null || true
            fi
            echo -e "${GREEN}STOPPED${NC}"
        fi
        rm -f "${PID_DIR}/celery.pid"
    fi

    # 2b. Stop Celery Browser PID
    if [ -f "${PID_DIR}/celery_browser.pid" ]; then
        local pid
        pid=$(cat "${PID_DIR}/celery_browser.pid")
        if kill -0 "${pid}" 2>/dev/null; then
            echo -n "Stopping Celery Browser Action Worker (PID: ${pid})... "
            kill -15 "${pid}" 2>/dev/null || true
            sleep 1
            if kill -0 "${pid}" 2>/dev/null; then
                kill -9 "${pid}" 2>/dev/null || true
            fi
            echo -e "${GREEN}STOPPED${NC}"
        fi
        rm -f "${PID_DIR}/celery_browser.pid"
    fi

    # 3. Stop Backend PID
    if [ -f "${PID_DIR}/backend.pid" ]; then
        local pid
        pid=$(cat "${PID_DIR}/backend.pid")
        if kill -0 "${pid}" 2>/dev/null; then
            echo -n "Stopping FastAPI Backend (PID: ${pid})... "
            kill -15 "${pid}" 2>/dev/null || true
            sleep 1
            if kill -0 "${pid}" 2>/dev/null; then
                kill -9 "${pid}" 2>/dev/null || true
            fi
            echo -e "${GREEN}STOPPED${NC}"
        fi
        rm -f "${PID_DIR}/backend.pid"
    fi

    # 3b. Stop Resource Monitor Daemon PID
    if [ -f "${PID_DIR}/monitor.pid" ]; then
        local pid
        pid=$(cat "${PID_DIR}/monitor.pid")
        if kill -0 "${pid}" 2>/dev/null; then
            echo -n "Stopping Resource Telemetry Recorder (PID: ${pid})... "
            kill -15 "${pid}" 2>/dev/null || true
            sleep 1
            if kill -0 "${pid}" 2>/dev/null; then
                kill -9 "${pid}" 2>/dev/null || true
            fi
            echo -e "${GREEN}STOPPED${NC}"
        fi
        rm -f "${PID_DIR}/monitor.pid"
    fi

    # 4. Clean up any leftover processes by pattern and port
    echo -n "Cleaning up lingering processes... "
    pkill -9 -f "socat TCP-LISTEN:${ALT_BACKEND_PORT}" 2>/dev/null || true
    pkill -9 -f "socat TCP-LISTEN:${ALT_DASHBOARD_PORT}" 2>/dev/null || true
    pkill -9 -f "resource_monitor.py --record" 2>/dev/null || true
    pkill -9 -f "uvicorn xbot.main:app" 2>/dev/null || true
    pkill -9 -f "celery.*xbot" 2>/dev/null || true
    pkill -9 -f "next" 2>/dev/null || true
    fuser -k "${DASHBOARD_PORT}/tcp" "${ALT_DASHBOARD_PORT}/tcp" 2>/dev/null || true
    fuser -k "${BACKEND_PORT}/tcp" "${ALT_BACKEND_PORT}/tcp" 2>/dev/null || true
    echo -e "${GREEN}DONE${NC}"

    # 5. Clean up stale browser lock files if any
    rm -f /tmp/xbot_lock_* 2>/dev/null || true

    echo -e "\n${BOLD}${GREEN}✅ All local XBot Pro services have been completely stopped.${NC}\n"
}

check_status() {
    echo -e "\n${BOLD}${BLUE}======================================================${NC}"
    echo -e "${BOLD}${BLUE}          📊 XBot Pro Service Status                  ${NC}"
    echo -e "${BOLD}${BLUE}======================================================${NC}\n"

    # Docker Production Stack Notice
    echo -e "${CYAN}🐳 Docker Stack Status:${NC}"
    if docker ps 2>/dev/null | grep -q "xbot"; then
        echo -e "  • Docker Stack (Portainer):         ${GREEN}● ACTIVE & RUNNING${NC}"
    else
        echo -e "  • Docker Stack (Portainer):         ${YELLOW}○ STOPPED / INACTIVE${NC}"
    fi
    echo ""
    echo -e "${CYAN}💻 Local Services (Primary: ${BACKEND_PORT}/${DASHBOARD_PORT} | Alt: ${ALT_BACKEND_PORT}/${ALT_DASHBOARD_PORT}):${NC}"

    # Local Backend
    if is_port_in_use "${BACKEND_PORT}"; then
        local health
        health=$(curl -s --max-time 2 "http://127.0.0.1:${BACKEND_PORT}/health" || echo "error")
        if echo "${health}" | grep -q "healthy"; then
            echo -e "  • Local Backend (Port ${BACKEND_PORT}):       ${GREEN}● RUNNING & HEALTHY${NC}"
        else
            echo -e "  • Local Backend (Port ${BACKEND_PORT}):       ${YELLOW}● RUNNING (Health check unresponsive)${NC}"
        fi
    else
        echo -e "  • Local Backend (Port ${BACKEND_PORT}):       ${RED}○ STOPPED${NC}"
    fi

    # Celery Task Worker
    if is_pid_running "${PID_DIR}/celery.pid"; then
        echo -e "  • Local Celery Task Worker & Beat:  ${GREEN}● RUNNING${NC} (PID: $(cat "${PID_DIR}/celery.pid"))"
    else
        echo -e "  • Local Celery Task Worker & Beat:  ${RED}○ STOPPED${NC}"
    fi

    # Celery Browser Worker
    if is_pid_running "${PID_DIR}/celery_browser.pid"; then
        echo -e "  • Local Celery Browser Action Eng:  ${GREEN}● RUNNING${NC} (PID: $(cat "${PID_DIR}/celery_browser.pid"))"
    else
        echo -e "  • Local Celery Browser Action Eng:  ${RED}○ STOPPED${NC}"
    fi

    # Local Dashboard
    if is_port_in_use "${DASHBOARD_PORT}"; then
        echo -e "  • Local Dashboard (Port ${DASHBOARD_PORT}):     ${GREEN}● RUNNING${NC} (http://localhost:${DASHBOARD_PORT})"
    else
        echo -e "  • Local Dashboard (Port ${DASHBOARD_PORT}):     ${RED}○ STOPPED${NC}"
    fi

    # Redis
    if command -v redis-cli >/dev/null 2>&1 && redis-cli ping >/dev/null 2>&1; then
        echo -e "  • Redis Server (Port 6379):         ${GREEN}● RUNNING & PONG${NC}"
    else
        echo -e "  • Redis Server (Port 6379):         ${YELLOW}○ UNKNOWN / NOT DETECTED${NC}"
    fi

    # Resource Telemetry Recorder
    if is_pid_running "${PID_DIR}/monitor.pid"; then
        local sample_count=0
        if [ -f "${LOG_DIR}/resource_telemetry.csv" ]; then
            sample_count=$(wc -l < "${LOG_DIR}/resource_telemetry.csv" 2>/dev/null | tr -d ' ')
            sample_count=$((sample_count > 0 ? sample_count - 1 : 0))
        fi
        echo -e "  • Resource Recorder (5m):           ${GREEN}● RUNNING${NC} (PID: $(cat "${PID_DIR}/monitor.pid"), ${sample_count} records)"
    else
        echo -e "  • Resource Recorder (5m):           ${RED}○ STOPPED${NC}"
    fi

    echo ""
}

show_logs() {
    local target=$1
    case "$target" in
        backend|api)
            tail -f -n 50 "${LOG_DIR}/backend.log"
            ;;
        celery|worker)
            tail -f -n 50 "${LOG_DIR}/celery.log"
            ;;
        dashboard|frontend|ui)
            tail -f -n 50 "${LOG_DIR}/dashboard.log"
            ;;
        *)
            echo "Usage: $0 logs [backend|celery|dashboard]"
            ;;
    esac
}

show_resources() {
    "${VENV_PYTHON}" "${PROJECT_ROOT}/scripts/resource_monitor.py" "$@"
}

monitor_resources() {
    local interval="${1:-3}"
    "${VENV_PYTHON}" "${PROJECT_ROOT}/scripts/resource_monitor.py" --watch "${interval}"
}

case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_services
        ;;
    status)
        check_status
        ;;
    stats|resources|usage)
        shift
        show_resources "$@"
        ;;
    history|trend|trends)
        shift
        "${VENV_PYTHON}" "${PROJECT_ROOT}/scripts/resource_monitor.py" --history "$@"
        ;;
    spikes|spike)
        "${VENV_PYTHON}" "${PROJECT_ROOT}/scripts/resource_monitor.py" --spikes
        ;;
    monitor|top|watch)
        shift
        monitor_resources "$@"
        ;;
    logs)
        show_logs "$2"
        ;;
    *)
        echo -e "Usage: ${BOLD}$0${NC} {${GREEN}start${NC}|${RED}stop${NC}|${YELLOW}restart${NC}|${BLUE}status${NC}|${CYAN}stats${NC}|${CYAN}history [hours]${NC}|${CYAN}spikes${NC}|${CYAN}monitor [interval]${NC}|${CYAN}logs [backend|celery|dashboard]${NC}}"
        exit 1
        ;;
esac

