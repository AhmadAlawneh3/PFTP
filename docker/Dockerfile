FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y iproute2 gosu && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source
COPY source/ /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create appuser
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Use entrypoint to fix permissions at runtime
ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["python", "service_manager.py"]
