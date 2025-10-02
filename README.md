# Cellframe Bridge Navigator

**Professional bridge monitoring system** for cross-chain transactions between Ethereum, BSC, and Cellframe networks.

A comprehensive Telegram bot and watcher service that provides real-time transaction tracking, fee estimation, and smart diagnostics for Cellframe ecosystem bridge operations.

## 🎯 Key Features

### For Users
- ✅ **Intuitive Bridge Interface** - Step-by-step guidance through bridge creation
- ✅ **Address Validation** - Real-time validation for ERC-20/BEP-20/CF-20 addresses
- ✅ **Fee Estimation** - Accurate fee calculations and time estimates
- ✅ **Transaction Tracking** - Monitor confirmations on both source and destination chains
- ✅ **Smart Diagnostics** - Automatic issue detection with actionable suggestions
- ✅ **Push Notifications** - Real-time updates on transaction status
- ✅ **Multi-Chain Support** - Ethereum, BSC, and Cellframe CF-20
- ✅ **Session Management** - Track multiple bridge sessions simultaneously
- ✅ **CFSCAN Integration** - Direct links to blockchain explorer

### For Developers
- ✅ **Production-Ready Architecture** - Microservices with health checks and graceful shutdown
- ✅ **Database Migrations** - Alembic for schema versioning
- ✅ **Real Blockchain Integration** - Live CF-20 RPC client with TX_HISTORY, MEMPOOL, TOKEN_INFO
- ✅ **EVM Transaction Tracker** - Confirmation counting for Ethereum and BSC
- ✅ **Smart Diagnostics Engine** - Automatic transaction analysis and issue detection
- ✅ **Notification System** - Push notifications with retry logic and backoff
- ✅ **CFSCAN API Client** - Full integration with blockchain explorer
- ✅ **Queue System** - Redis RQ for reliable event processing
- ✅ **Docker Compose** - Full stack orchestration

## 🏗️ Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Telegram   │────────►│  Bot Service │────────►│  PostgreSQL  │
│    Users     │         │   (aiogram)  │         │   Database   │
└──────────────┘         └───────┬──────┘         └──────────────┘
                                 │
                                 ▼
                         ┌──────────────┐
                         │    Redis     │
                         │ Queue/Cache  │
                         └───────┬──────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │  ETH Watcher │ │  BSC Watcher │ │ CF-20 Watcher│
        └───────┬──────┘ └───────┬──────┘ └───────┬──────┘
                │                │                │
                ▼                ▼                ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ Ethereum RPC │ │   BSC RPC    │ │ Cellframe    │
        │   + Scan     │ │   + Scan     │ │ Node RPC     │
        └──────────────┘ └──────────────┘ └──────────────┘
```

## 📦 Components

### `bot/` - Telegram Bot
- **Modern UX** with inline keyboards and step-by-step flows
- **Command handlers**: `/bridge`, `/status`, `/fees`, `/bind`, `/mysessions`
- **FSM-based flows** for bridge creation and address binding
- **Address validation** before submission

### `watcher/` - Blockchain Monitoring
- **CF-20 RPC Client** - Full JSON-RPC integration (TX_HISTORY, MEMPOOL, TOKEN_INFO)
- **Ethereum Watcher** - CELL ERC-20 token tracking with confirmation counting
- **BSC Watcher** - CELL BEP-20 token tracking with confirmation counting
- **Fee Estimator** - Real-time gas price and transaction cost estimation
- **Address Validators** - Format validation for all supported chains

### `data/` - Data Layer
- **SQLAlchemy 2.0** models with typed relationships
- **Alembic migrations** for schema versioning
- **AsyncPG** for high-performance database access
- **Models**: User, WalletBinding, BridgeSession, Transaction, Alert

### `queue/` - Event Processing
- **Redis RQ** for reliable job processing
- **Retry mechanism** for failed jobs
- **Event processing pipeline** for blockchain events

## 🚀 Quick Start

### Minimal Mode (Bot Only) ⚡

**Just want to try the bot? Start with only Telegram token:**

See **[MINIMAL_MODE.md](MINIMAL_MODE.md)** for bot-only setup (no blockchain monitoring).

```bash
cp env.minimal.example .env
# Edit .env: add your TELEGRAM_BOT_TOKEN
docker-compose -f docker-compose.minimal.yml up
```

### Full Mode (With Blockchain Monitoring)

See **[SETUP.md](SETUP.md)** for complete installation with blockchain monitoring.

### Prerequisites

- Docker and Docker Compose
- Telegram Bot Token ([Get from BotFather](https://t.me/BotFather))
- RPC endpoints (Ethereum, BSC, Cellframe node) - *optional for minimal mode*

### Installation

1. **Clone repository**
```bash
git clone <repository-url>
cd Cellframe-navigator
```

2. **Configure environment**
```bash
cp env.example .env
# Edit .env with your credentials
```

3. **Launch services**
```bash
docker-compose up --build
```

Services will start in this order:
1. PostgreSQL & Redis (with health checks)
2. Database migrations
3. Bot, Watcher, and Worker services

### Environment Variables

**Required:**
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `CF_RPC_URL` - Cellframe node RPC endpoint (e.g., `http://node:8079`)
- `CF_NETWORK` - Cellframe network (`backbone` or `kelvpn`)

**Recommended:**
- `ETH_RPC_URL` - Ethereum RPC (Infura/Alchemy)
- `ETHERSCAN_API_KEY` - For transaction verification
- `BSC_RPC_URL` - BSC RPC endpoint
- `BSCSCAN_API_KEY` - For BSC verification

See `env.example` for all configuration options.

## 🎮 Bot Commands

| Command | Description |
|---------|-------------|
| `/start`, `/help` | Show welcome message and available commands |
| `/bridge` | Start new bridge session with step-by-step guidance |
| `/status [tx_hash]` | Check transaction status or view your sessions |
| `/fees` | View current bridge fees and time estimates |
| `/bind` | Bind blockchain addresses for quick access |
| `/mysessions` | View all your bridge sessions |
| `/cancel` | Cancel current operation |

## 💻 Development

### Local Setup

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Start infrastructure
docker-compose up db redis

# Run migrations
alembic upgrade head

# Run services
python -m bot.main      # Terminal 1
python -m watcher.main  # Terminal 2
python -m queue.worker  # Terminal 3
```

### Project Structure

```
.
├── alembic/              # Database migrations
├── bot/                  # Telegram bot service
│   ├── config.py         # Configuration
│   ├── handlers.py       # Command handlers with FSM
│   ├── keyboards.py      # Inline keyboards
│   └── storage.py        # Session storage
├── watcher/              # Blockchain monitoring
│   ├── chains/           # Chain-specific watchers
│   ├── cf20_rpc.py       # CF-20 JSON-RPC client
│   ├── evm_tracker.py    # EVM confirmation tracker
│   ├── validators.py     # Address validators
│   └── fee_estimator.py  # Fee calculation
├── data/                 # Data layer
│   ├── database.py       # Database connection
│   ├── models.py         # SQLAlchemy models
│   └── repositories.py   # Data access layer
├── queue/                # Queue processing
└── docker-compose.yml    # Service orchestration
```

## 🔧 Technical Stack

- **Python 3.11+** - Modern async/await patterns
- **aiogram 3.0** - Telegram Bot framework
- **SQLAlchemy 2.0** - ORM with async support
- **PostgreSQL 15** - Relational database
- **Redis 7** - Queue and cache
- **Web3.py** - Ethereum/BSC interaction
- **httpx** - Async HTTP client for CF-20 RPC
- **Alembic** - Database migrations
- **Docker** - Containerization

## 📝 What's Implemented

Recently added:
- [x] **Smart diagnostics** in `/status` command
- [x] **Push notification service** for transaction updates
- [x] **CFSCAN integration** for public verification
- [x] **Transaction diagnostics** with actionable suggestions
- [x] **Progress tracking** with visual progress bars
- [x] **Error detection** with troubleshooting steps

Coming soon:
- [ ] Multi-language support (EN/RU/TH)
- [ ] Web dashboard for support team  
- [ ] Transaction history export
- [ ] Advanced analytics dashboard

## 🔒 Security

- ✅ Bot operates in **read-only mode** - no private keys required
- ✅ Address validation before processing
- ✅ Environment-based secrets management
- ✅ No sensitive data in logs
- ✅ Rate limiting ready
- ✅ Whitelist support for authorized users

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions welcome! Please read the contribution guidelines first.

## 📞 Support

- Documentation: See [SETUP.md](SETUP.md)
- Issues: GitHub Issues
- Contact: dev@cellframe.net
