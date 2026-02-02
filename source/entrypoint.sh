#!/bin/bash
set -e

# Note: directories are volume-mounted from host, no need to create them
if [ -d "/app/data/tools" ] && [ -d "/app/data/uploads" ]; then
    # Ensure directories are accessible by both container (appuser) and host user
    chmod 777 /app/data/tools /app/data/uploads
fi

# Switch to appuser and execute the main command
exec gosu appuser "$@"
