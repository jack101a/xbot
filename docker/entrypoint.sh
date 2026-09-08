#!/bin/sh
set -e

# Set timezone (defaults to Asia/Kolkata - IST)
TZ="${TZ:-Asia/Kolkata}"
export TZ
if [ -f "/usr/share/zoneinfo/$TZ" ]; then
    ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime && echo "$TZ" > /etc/timezone
fi

# Ensure basic app data directories exist
mkdir -p /app/data/profiles /app/data/logs /app/data/media

# Seed default profile if destination has no profiles
if [ -d "/app/defaults/profiles" ] && [ -z "$(ls -A /app/data/profiles 2>/dev/null)" ]; then
    echo "Initializing default profiles into /app/data/profiles..."
    cp -r /app/defaults/profiles/* /app/data/profiles/ 2>/dev/null || true
fi

# Adjust permissions for PUID and PGID
if [ -n "$PUID" ] && [ -n "$PGID" ]; then
    chown -R "$PUID:$PGID" /app/data 2>/dev/null || true
fi

umask 0002

exec "$@"
