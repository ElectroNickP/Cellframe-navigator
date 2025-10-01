FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY bot /app/bot
COPY watcher /app/watcher
COPY data /app/data
COPY queue /app/queue

RUN pip install --upgrade pip && pip install -e .

CMD ["python", "bot/main.py"]
