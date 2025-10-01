# Cellframe Navigator

Cellframe Navigator is a reference implementation of a Telegram bot and watcher service
that orchestrate cross-chain bridge monitoring for the Cellframe ecosystem. The
project is split into multiple services that communicate via Redis queues and a
shared PostgreSQL database.

## Architecture Overview

```
Telegram Bot (aiogram) <---> Redis (RQ queues) <---> Watcher (chain pollers)
            |                                   \
            |                                    --> PostgreSQL (SQLAlchemy models)
            \---> Users receive alerts based on bridge sessions and transactions
```

### Components

- **`bot/`** – Telegram bot with handlers for `/bridge`, `/status`, `/fees`, `/bind`,
  and `/help`. The bot guides the user through bridge direction and token selection,
  stores bindings, and listens for notifications coming from the watcher through
  Redis queues.
- **`watcher/`** – Blockchain polling service with dedicated modules for Ethereum,
  Binance Smart Chain, and Cellframe CF-20. Each watcher polls RPC endpoints and
  enqueues events for further processing.
- **`data/`** – Data access layer powered by SQLAlchemy with models for `user`,
  `wallet_binding`, `bridge_session`, `tx`, and `alert` entities.
- **`queue/`** – RQ queue tasks and worker to process watcher events, retry failed
  jobs, and dispatch bot notifications.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Telegram bot token (obtain from [BotFather](https://t.me/BotFather))
- RPC credentials for Ethereum/BSC/Cellframe (optional for local testing)

### Environment Variables

Copy the example environment file and adjust values as needed:

```bash
cp .env.example .env
```

Required variables:

- `TELEGRAM_BOT_TOKEN` – Telegram bot token
- `DATABASE_URL` – SQLAlchemy connection string (defaults to Postgres in docker-compose)
- `REDIS_URL` – Redis connection URL
- `ETH_RPC_URL` / `ETHERSCAN_API_KEY` – Ethereum RPC and optional explorer API key
- `BSC_RPC_URL` / `BSCSCAN_API_KEY` – BSC RPC and optional explorer API key
- `CF_RPC_URL` – Cellframe node RPC endpoint

### Running with Docker Compose

Launch the full stack (bot, watcher, worker, Postgres, Redis):

```bash
docker-compose up --build
```

The bot will start polling Telegram updates while the watcher continuously polls
blockchains and enqueues new events for processing.

### Local Development

1. Install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

2. Create a Postgres database and run migrations (Alembic not included in this
   skeleton, models are provided for reference).

3. Start Redis and Postgres services locally or via Docker Compose.

4. Run individual services:

   ```bash
   python -m bot.main
   python -m watcher.main
   python -m queue.worker
   ```

### Retry Queue

The project leverages Redis + RQ for processing events emitted by the watcher.
Failed jobs can be retried automatically by RQ, ensuring that notifications are
eventually delivered to bot users.

## Project Structure

```
bot/            # Telegram bot implementation
watcher/        # Chain polling services and schedulers
data/           # SQLAlchemy models and session helpers
queue/          # RQ tasks and worker
Dockerfile
docker-compose.yml
pyproject.toml
```

## License

MIT
