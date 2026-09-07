#!/usr/bin/env bash
# XBot Production Backup & Rotation Script
# Retains the last 7 days of system state archives (SQLite DB + profile JSONL/YAML logs)

set -euo pipefail

# Directory paths
PROJECT_ROOT="/home/ubuntu/projects/xbot"
BACKUP_DIR="${PROJECT_ROOT}/backups"
PROFILES_DIR="${PROJECT_ROOT}/data/profiles"
DB_FILE="${PROJECT_ROOT}/xbot.db"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEMP_BACKUP_DIR="${BACKUP_DIR}/xbot_backup_${TIMESTAMP}"
ARCHIVE_FILE="${BACKUP_DIR}/xbot_state_${TIMESTAMP}.tar.gz"

echo "=== XBot Backup Starting at $(date) ==="

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Create temporary staging folder
mkdir -p "${TEMP_BACKUP_DIR}"

# 1. Back up SQLite Database safely (using sqlite3 .backup if command exists, fallback to cp)
if command -v sqlite3 &> /dev/null; then
    echo "Using sqlite3 to perform online database hot backup..."
    sqlite3 "${DB_FILE}" ".backup '${TEMP_BACKUP_DIR}/xbot.db'"
else
    echo "sqlite3 CLI not found, performing copy backup..."
    cp "${DB_FILE}" "${TEMP_BACKUP_DIR}/xbot.db"
fi

# 2. Back up User Profile configurations and logs
if [ -d "${PROFILES_DIR}" ]; then
    echo "Copying profile configurations, diaries, and memories..."
    cp -r "${PROFILES_DIR}" "${TEMP_BACKUP_DIR}/profiles"
else
    echo "Warning: Profiles directory not found at ${PROFILES_DIR}."
fi

# 3. Create compressed tarball archive
echo "Compressing system state backup..."
tar -czf "${ARCHIVE_FILE}" -C "${BACKUP_DIR}" "xbot_backup_${TIMESTAMP}"

# 4. Clean up temporary directory
rm -rf "${TEMP_BACKUP_DIR}"

echo "Backup written successfully: ${ARCHIVE_FILE}"

# 5. Backup Rotation (Retain only the last 7 daily archives)
echo "Running archive retention policy (keep last 7 backups)..."
# List matching files, sort by time, skip the first 7, and delete the rest
find "${BACKUP_DIR}" -name "xbot_state_*.tar.gz" -type f -printf '%T@ %p\n' \
    | sort -nr \
    | tail -n +8 \
    | cut -d' ' -f2- \
    | while read -r old_archive; do
        if [ -n "${old_archive}" ]; then
            echo "Deleting old archive: ${old_archive}"
            rm -f "${old_archive}"
        fi
    done

echo "=== Backup & Rotation Finished Successfully ==="
