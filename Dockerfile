FROM python:3.11-slim

# Base environment variables (stable layer)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies (stable layer)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        git && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies (relatively stable)
COPY pyproject.toml README.md /app/
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e . && \
    pip cache purge

# Copy application code (changes frequently - last layer)
COPY alembic.ini /app/
COPY alembic /app/alembic
COPY bot /app/bot
COPY watcher /app/watcher
COPY data /app/data
COPY tasks /app/tasks

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "bot.main"]
