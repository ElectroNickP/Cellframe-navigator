# Cellframe Bridge Navigator - Setup Guide

## Overview

Cellframe Bridge Navigator is a comprehensive Telegram bot and monitoring system for tracking cross-chain bridge transactions between Ethereum, BSC, and Cellframe networks.

## Features Implemented

### Core Infrastructure
- ✅ Alembic database migrations
- ✅ PostgreSQL data models with relationships
- ✅ Redis queue system for event processing
- ✅ Docker Compose orchestration with health checks

### Blockchain Integration
- ✅ CF-20 JSON-RPC client (TX_HISTORY, MEMPOOL, TOKEN_INFO)
- ✅ Ethereum watcher with ERC-20 CELL token tracking
- ✅ BSC watcher with BEP-20 CELL token tracking
- ✅ Transaction confirmation tracking for all chains
- ✅ Real-time mempool monitoring

### Telegram Bot
- ✅ Improved UX with step-by-step bridge creation
- ✅ Address validation (ERC-20/BEP-20/CF-20)
- ✅ Source and destination address input
- ✅ Confirmation flow before session creation
- ✅ Bridge session management
- ✅ Fee estimation service

### Additional Features
- ✅ Multi-chain transaction tracking
- ✅ Address binding system
- ✅ Bridge fee calculator
- ✅ Estimated completion time

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- RPC endpoints (Ethereum, BSC, Cellframe)

### 2. Configuration

Copy the example environment file:

```bash
cp env.example .env
```

Edit `.env` and fill in required values:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Ethereum
ETH_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
ETHERSCAN_API_KEY=your_etherscan_key

# BSC
BSC_RPC_URL=https://bsc-dataseed1.ninicoin.io
BSCSCAN_API_KEY=your_bscscan_key

# Cellframe
CF_RPC_URL=http://your-cellframe-node:8079
CF_NETWORK=backbone
```

### 3. Launch Services

Build and start all services:

```bash
docker-compose up --build
```

This will start:
- **PostgreSQL** - Database
- **Redis** - Queue and cache
- **Migration** - Run database migrations
- **Bot** - Telegram bot service
- **Watcher** - Blockchain monitoring service
- **Worker** - Queue worker for event processing

### 4. Verify Services

Check logs:

```bash
# Bot logs
docker-compose logs -f bot

# Watcher logs
docker-compose logs -f watcher

# All services
docker-compose logs -f
```

### 5. Test Bot

Open Telegram and send `/start` to your bot.

## Architecture

```
┌─────────────┐
│ Telegram    │
│ Bot         │◄──── Users interact via Telegram
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐
│  Bot        │────►│  PostgreSQL  │
│  Service    │     │  Database    │
└──────┬──────┘     └──────────────┘
       │
       ▼
┌─────────────┐
│   Redis     │
│   Queue     │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐
│  Watcher    │────►│  Blockchain  │
│  Service    │     │  RPC Nodes   │
└──────┬──────┘     └──────────────┘
       │
       ▼
┌─────────────┐
│  Worker     │
│  Service    │
└─────────────┘
```

## Database Schema

### Tables

- **users** - Telegram users
- **wallet_bindings** - User's blockchain addresses
- **bridge_sessions** - Bridge transactions
- **transactions** - Blockchain transactions with confirmation tracking
- **alerts** - Notification queue

### Key Fields

**bridge_sessions:**
- `session_id` - Unique session identifier
- `direction` - Bridge direction (eth_to_cf, bsc_to_cf, etc.)
- `src_address` / `dst_address` - Source and destination addresses
- `estimated_fee` / `estimated_time_seconds` - Fee and time estimates

**transactions:**
- `confirmations` / `confirmations_required` - Confirmation tracking
- `block_number` - Block where transaction was included
- `error_message` - Error details if failed

## Bot Commands

### User Commands

- `/start` or `/help` - Show help message
- `/bridge` - Start new bridge session
- `/status [tx_hash]` - Check transaction status
- `/fees` - View current bridge fees
- `/bind` - Bind blockchain addresses
- `/mysessions` - View your bridge sessions
- `/cancel` - Cancel current operation

### Bridge Flow

1. Choose direction (ETH→CF, BSC→CF, CF→ETH, CF→BSC)
2. Select token (CELL, KEL, USDT, etc.)
3. Enter source address (validated)
4. Enter destination address (validated)
5. Enter amount
6. Confirm and create session

## Development

### Local Development (without Docker)

1. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. Start PostgreSQL and Redis:

```bash
docker-compose up db redis
```

3. Run migrations:

```bash
alembic upgrade head
```

4. Run services:

```bash
# Terminal 1
python -m bot.main

# Terminal 2
python -m watcher.main

# Terminal 3
python -m queue.worker
```

### Project Structure

```
.
├── alembic/              # Database migrations
│   └── versions/         # Migration scripts
├── bot/                  # Telegram bot
│   ├── config.py         # Configuration
│   ├── handlers.py       # Command handlers
│   ├── keyboards.py      # Inline keyboards
│   └── storage.py        # In-memory storage
├── data/                 # Data layer
│   ├── database.py       # Database connection
│   ├── models.py         # SQLAlchemy models
│   └── repositories.py   # Data access
├── watcher/              # Blockchain monitoring
│   ├── chains/           # Chain-specific watchers
│   │   ├── base.py       # Base watcher class
│   │   ├── eth.py        # Ethereum watcher
│   │   ├── bsc.py        # BSC watcher
│   │   └── cf20.py       # Cellframe watcher
│   ├── cf20_rpc.py       # CF-20 RPC client
│   ├── evm_tracker.py    # EVM transaction tracker
│   ├── validators.py     # Address validators
│   ├── fee_estimator.py  # Fee calculation
│   └── schedulers/       # Polling scheduler
├── queue/                # Queue processing
│   ├── tasks.py          # Queue tasks
│   └── worker.py         # Queue worker
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Container image
└── pyproject.toml        # Python dependencies
```

## Troubleshooting

### Bot not responding

1. Check bot token is correct
2. Verify bot service is running: `docker-compose ps`
3. Check logs: `docker-compose logs bot`

### Watcher not tracking transactions

1. Verify RPC endpoints are accessible
2. Check network configuration (mainnet/testnet)
3. Review watcher logs: `docker-compose logs watcher`

### Database connection errors

1. Ensure PostgreSQL is healthy: `docker-compose ps db`
2. Check DATABASE_URL in `.env`
3. Verify migrations ran: `docker-compose logs migration`

### Redis connection issues

1. Check Redis is running: `docker-compose ps redis`
2. Verify REDIS_URL in `.env`
3. Test connection: `docker-compose exec redis redis-cli ping`

## Next Steps (Coming Soon)

- [ ] Smart transaction diagnostics in `/status`
- [ ] Push notifications for transaction updates
- [ ] CFSCAN integration for public verification
- [ ] Multi-language support (EN/RU/TH)
- [ ] Web dashboard for support team
- [ ] Transaction history export

## Security Notes

⚠️ **Important:**
- Never commit `.env` file with real credentials
- Keep RPC endpoints secured (use private nodes or API keys)
- Bot reads blockchain data only (no private keys needed)
- Use environment variables for all secrets
- Enable Telegram bot privacy mode if needed

## Support

For issues or questions:
1. Check logs first
2. Review this documentation
3. Contact development team

## License

MIT License - see LICENSE file for details


