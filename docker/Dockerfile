FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y iproute2 gosu libcap2-bin && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source
COPY source/ /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create appuser and fix permissions
RUN adduser -u 5678 --disabled-password --gecos "" appuser && \
    chown -R appuser /app && \
    chmod -R 755 /app

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Grant Python the capability to bind to privileged ports (< 1024)
# This allows non-root appuser to bind to FTP (21) and SMB (445) ports
RUN setcap cap_net_bind_service=+ep /usr/local/bin/python3.11

# Use entrypoint to fix permissions at runtime
ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["python", "service_manager.py"]
