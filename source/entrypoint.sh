#!/bin/bash
set -e

# Create data directories if they don't exist (for development/testing)
mkdir -p /app/data/tools /app/data/uploads

# Get the owner of the mounted tools volume (actual mount point)
if [ -d "/app/data/tools" ]; then
    TARGET_UID=$(stat -c "%u" /app/data/tools)
    TARGET_GID=$(stat -c "%g" /app/data/tools)

    # Only update appuser if UID is not root (0)
    if [ "$TARGET_UID" != "0" ]; then
        usermod -u "$TARGET_UID" appuser 2>/dev/null || true
        groupmod -g "$TARGET_GID" appuser 2>/dev/null || true
    fi
fi

# Ensure appuser owns the directories
chown -R appuser:appuser /app/data

# Switch to appuser and execute the main command
exec gosu appuser "$@"
