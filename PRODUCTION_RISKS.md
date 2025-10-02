# 🚨 Production Risks & Pitfalls Analysis

**Date**: 2025-10-03  
**Severity Levels**: 🔴 Critical | 🟡 High | 🟠 Medium | 🟢 Low

---

## 🔴 CRITICAL RISKS (Must Address Before Production)

### 1. RPC Node Failures & Rate Limits
**Severity**: 🔴 Critical  
**Likelihood**: Very High (90%)

**Problem**:
```python
# In watcher/evm_tracker.py, cf20_rpc.py
# Direct RPC calls without retry logic or fallback
response = requests.post(self.rpc_url, json=payload)
```

**What will happen**:
- Public RPC nodes (Infura, Alchemy) have rate limits
- `http://rpc.cellframe.net` went down (we saw this!)
- Bot will crash or hang on every RPC failure
- Users see "Error tracking transaction" constantly

**Real scenario**:
```
User: /track 0x123...
Bot: ❌ RPC node temporarily unavailable
User: /track 0x123... (tries again)
Bot: ❌ RPC node temporarily unavailable
User: (leaves chat, never comes back)
```

**Solution**:
```python
# Add retry logic with exponential backoff
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_transaction(self, tx_hash: str):
    # Your RPC call here
    pass

# Add fallback RPC nodes
self.rpc_urls = [
    "https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY",
    "https://mainnet.infura.io/v3/YOUR_KEY",
    "https://rpc.ankr.com/eth"
]
```

**Impact if not fixed**: 🔴 Bot becomes unusable during peak hours

---

### 2. Database Connection Pool Exhaustion
**Severity**: 🔴 Critical  
**Likelihood**: High (70%)

**Problem**:
```python
# In multiple handlers
async with SessionFactory() as db_session:
    # Long-running operation
    await some_slow_rpc_call()  # Takes 10+ seconds
    # Connection held open entire time!
```

**What will happen**:
- PostgreSQL default: 100 connections
- Each bot request holds connection during RPC calls
- 100 simultaneous users = all connections exhausted
- New users get: "Connection pool exhausted"
- Bot stops responding completely

**Real scenario**:
```
10:00 - 50 users tracking TXs (50 connections)
10:05 - 100 users (100 connections) - POOL FULL
10:06 - User 101: "Bot doesn't respond!"
10:07 - User 102-200: All failing
10:10 - Support flooded with tickets
```

**Solution**:
```python
# 1. Separate RPC calls from DB operations
tx_info = await self.get_tx_info(tx_hash)  # No DB connection here

# 2. Then save to DB quickly
async with SessionFactory() as db_session:
    await tx_repo.create(...)  # Fast operation
    await db_session.commit()

# 3. Configure connection pool
# In data/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,  # Max connections
    max_overflow=40,  # Extra connections under load
    pool_pre_ping=True,  # Check connection health
    pool_recycle=3600  # Recycle connections every hour
)
```

**Impact if not fixed**: 🔴 Bot crashes under moderate load (100+ users)

---

### 3. Memory Leaks from Unclosed Sessions
**Severity**: 🔴 Critical  
**Likelihood**: Medium (50%)

**Problem**:
```python
# If exception occurs before session closes
async with SessionFactory() as db_session:
    result = await some_operation()
    # Exception here! Session might not close properly
    await db_session.commit()
```

**What will happen**:
- Unclosed SQLAlchemy sessions accumulate
- Memory usage grows: 100MB → 500MB → 1GB → OOM
- Docker container killed: "Out of memory"
- Bot restarts, loses state

**Real scenario**:
```
Day 1: Bot uses 150MB RAM ✅
Day 2: Bot uses 300MB RAM 🟡
Day 3: Bot uses 800MB RAM 🟠
Day 4: OOM Kill - Bot crashes 🔴
Day 5: Repeat cycle...
```

**Solution**:
```python
# Always use try-finally
async def track_transaction(tx_hash: str):
    session = SessionFactory()
    try:
        # Your operations
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()  # ALWAYS close

# Or better - use context manager properly
# (Already doing this, but watch for edge cases)
```

**Impact if not fixed**: 🔴 Bot crashes every 3-7 days

---

## 🟡 HIGH RISKS (Should Address Soon)

### 4. Telegram API Rate Limits
**Severity**: 🟡 High  
**Likelihood**: Very High (80%)

**Problem**:
```python
# tx_monitor sends updates every 30 seconds
await bot.send_message(user_id, notification)
```

**Telegram limits**:
- 30 messages per second to different users
- 1 message per second to same user
- Violations = bot gets banned temporarily

**What will happen**:
```
09:00 - 200 users tracking TXs
09:05 - Monitor sends 200 notifications simultaneously
09:05:01 - Telegram: "429 Too Many Requests"
09:05:02 - Bot banned for 60 seconds
09:05:03 - 100 more notifications queue up
09:06:03 - Bot unbanned, sends 300 messages
09:06:04 - Banned again for longer...
```

**Solution**:
```python
# Add rate limiting
from aiogram.utils.chat_action import ChatActionSender
import asyncio

async def send_with_rate_limit(bot, user_id, text):
    # Maximum 20 messages per second
    await asyncio.sleep(0.05)  # 50ms between messages
    try:
        await bot.send_message(user_id, text)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await bot.send_message(user_id, text)
```

**Impact if not fixed**: 🟡 Bot gets temporarily banned during peak hours

---

### 5. Blockchain Reorganizations (Chain Reorgs)
**Severity**: 🟡 High  
**Likelihood**: Medium (40%)

**Problem**:
```python
# Bot says TX confirmed at block 1000
# Chain reorg happens, block 1000 gets replaced
# TX now in block 1002 or disappeared completely
```

**What will happen**:
```
User: Tracks TX in block 1000
Bot: ✅ Transaction Confirmed! (12/12 confirmations)
[Chain reorg happens]
Reality: TX now in block 1002 (only 10 confirmations)
User: "Where are my tokens?!" 😱
```

**Real scenario**:
- Ethereum: Rare but happens (1% of blocks)
- BSC: More common (5% of blocks)
- Cellframe: Unknown, but possible

**Solution**:
```python
# Wait for MORE confirmations than minimum
ETH_CONFIRMATIONS_SAFE = 20  # Instead of 12
BSC_CONFIRMATIONS_SAFE = 25  # Instead of 15

# Monitor for reorgs
last_known_block = tx.block_number
current_tx = await get_transaction(tx_hash)
if current_tx.block_number != last_known_block:
    # Reorg detected!
    await notify_user(
        "⚠️ Blockchain reorganization detected. "
        "Your transaction is being re-confirmed."
    )
```

**Impact if not fixed**: 🟡 Users lose trust, support tickets increase

---

### 6. Stale RPC Data / Caching Issues
**Severity**: 🟡 High  
**Likelihood**: High (60%)

**Problem**:
```python
# Some RPC nodes cache responses for 30-60 seconds
current_block = web3.eth.block_number  # Cached!
# User sees: "2/12 confirmations"
# Reality: Already 8/12 confirmations
```

**What will happen**:
```
User tracks fresh TX
Bot: "1/12 confirmations" ✅
30 seconds later...
Bot: "1/12 confirmations" (should be 3/12) ❌
User: "Bot is broken, stuck at 1/12"
```

**Solution**:
```python
# Force fresh data
web3 = Web3(HTTPProvider(
    rpc_url,
    request_kwargs={'headers': {'Cache-Control': 'no-cache'}}
))

# Or use latest block with offset
safe_block = current_block - 1  # Always use confirmed block
```

**Impact if not fixed**: 🟡 Users think bot is broken

---

## 🟠 MEDIUM RISKS (Monitor & Plan)

### 7. Gas Price Spikes Breaking Fee Estimates
**Severity**: 🟠 Medium  
**Likelihood**: High (70%)

**Problem**:
```python
# In watcher/fee_estimator.py
estimated_fee = 0.003  # Hardcoded!
```

**What will happen**:
```
Normal day: Gas = 20 gwei, fee = 0.003 ETH ✅
NFT mint day: Gas = 500 gwei, fee = 0.075 ETH ❌
User sends 0.003 ETH fee
Bot: "✅ Estimated fee: 0.003 ETH"
Reality: TX stuck in mempool forever
User: "My tokens are lost!"
```

**Solution**:
```python
# Get real-time gas prices
async def estimate_bridge_fee(self, chain: str) -> float:
    if chain == "ethereum":
        gas_price = await web3.eth.gas_price
        gas_units = 100000  # Typical bridge TX
        fee_wei = gas_price * gas_units
        fee_eth = web3.from_wei(fee_wei, 'ether')
        return float(fee_eth) * 1.2  # Add 20% buffer
```

**Impact if not fixed**: 🟠 Users lose money on failed TXs

---

### 8. Database Migration Failures in Production
**Severity**: 🟠 Medium  
**Likelihood**: Medium (40%)

**Problem**:
```python
# docker-compose.yml runs migration on startup
migration:
  command: alembic upgrade head
  
# If migration fails, entire stack fails to start
```

**What will happen**:
```
Deploy new version
Migration starts...
Migration fails (syntax error in SQL)
Bot doesn't start
Users: "Bot is down!" for hours
Team: Scrambling to fix
```

**Solution**:
```python
# 1. Test migrations on staging first
# 2. Add migration health check
migration:
  command: |
    alembic upgrade head || (
      echo "Migration failed! Rolling back..." &&
      alembic downgrade -1 &&
      exit 1
    )

# 3. Separate migration from deployment
# Run migrations manually, verify, then deploy bot
```

**Impact if not fixed**: 🟠 Deployment downtime 1-4 hours

---

### 9. TX Monitor Sending Duplicate Notifications
**Severity**: 🟠 Medium  
**Likelihood**: Medium (50%)

**Problem**:
```python
# tx_monitor checks every 30 seconds
# If TX goes from 11 → 12 confirmations
# And monitor runs twice due to timing
# User gets notification TWICE
```

**What will happen**:
```
10:00:00 - TX at 11/12 confirmations
10:00:30 - Monitor: "TX confirmed!" notification sent
10:00:31 - Monitor runs again (race condition)
10:00:31 - Monitor: "TX confirmed!" notification sent AGAIN
User: "Why spam me?"
```

**Solution**:
```python
# Add notification deduplication
class TransactionMonitor:
    def __init__(self):
        self.notified_txs = set()
    
    async def _send_confirmation_notification(self, tx_hash, user_id):
        notification_key = f"{tx_hash}:{user_id}:confirmed"
        
        if notification_key in self.notified_txs:
            return  # Already notified
        
        await bot.send_message(user_id, "✅ Transaction confirmed!")
        self.notified_txs.add(notification_key)
```

**Impact if not fixed**: 🟠 Users annoyed by spam

---

### 10. Docker Container Restart Losing In-Memory State
**Severity**: 🟠 Medium  
**Likelihood**: High (70%)

**Problem**:
```python
# tx_monitor keeps notified_txs in memory
# Container restarts (deployment, crash, etc)
# All in-memory data LOST
# Users get duplicate notifications
```

**What will happen**:
```
User tracks TX, gets "confirmed" notification
Container restarts (new deployment)
Monitor starts fresh, no memory of past notifications
Monitor: "TX confirmed!" notification sent AGAIN
User: "Stop spamming!"
```

**Solution**:
```python
# Store notification state in Redis
import redis.asyncio as redis

async def _send_confirmation_notification(self, tx_hash, user_id):
    key = f"notified:{tx_hash}:{user_id}:confirmed"
    
    # Check Redis
    already_sent = await self.redis.get(key)
    if already_sent:
        return
    
    # Send notification
    await bot.send_message(user_id, "✅ Transaction confirmed!")
    
    # Mark as sent in Redis (expires in 7 days)
    await self.redis.setex(key, 604800, "1")
```

**Impact if not fixed**: 🟠 Users get spam after every deployment

---

## 🟢 LOW RISKS (Nice to Have)

### 11. Old Tracked TXs Never Cleaned Up
**Severity**: 🟢 Low  
**Likelihood**: High (80%)

**Problem**:
- Users track TX, get notification, never check again
- TX stays in database forever
- Database grows: 1MB → 100MB → 1GB → 10GB

**Solution**:
```python
# Add cleanup job
async def cleanup_old_transactions():
    """Remove confirmed TXs older than 30 days."""
    cutoff_date = datetime.now() - timedelta(days=30)
    await tx_repo.delete_old_confirmed(cutoff_date)
```

---

### 12. No Monitoring/Alerting
**Severity**: 🟢 Low (but important!)  
**Likelihood**: 100%

**Problem**:
- Bot crashes, you don't know until users complain
- RPC fails, no alert
- Database full, no warning

**Solution**:
```python
# Add health check endpoint
@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "rpc_eth": await check_rpc("eth"),
        "rpc_bsc": await check_rpc("bsc"),
        "rpc_cf": await check_rpc("cf"),
        "database": await check_db(),
        "redis": await check_redis()
    }

# Set up monitoring (Uptime Robot, Grafana, etc.)
```

---

## 📊 RISK SUMMARY TABLE

| Risk | Severity | Likelihood | Impact | Priority |
|------|----------|------------|--------|----------|
| RPC Failures | 🔴 Critical | 90% | Bot unusable | 1 |
| DB Pool Exhaustion | 🔴 Critical | 70% | Bot crashes | 2 |
| Memory Leaks | 🔴 Critical | 50% | Crashes every week | 3 |
| Telegram Rate Limits | 🟡 High | 80% | Temporary bans | 4 |
| Chain Reorgs | 🟡 High | 40% | User trust lost | 5 |
| Stale RPC Data | 🟡 High | 60% | Wrong confirmations | 6 |
| Gas Price Spikes | 🟠 Medium | 70% | Wrong estimates | 7 |
| Migration Failures | 🟠 Medium | 40% | Deployment fails | 8 |
| Duplicate Notifications | 🟠 Medium | 50% | User annoyance | 9 |
| Lost In-Memory State | 🟠 Medium | 70% | Spam after restart | 10 |

---

## 🎯 ACTION PLAN

### Phase 1: Before Production (MUST DO)
1. ✅ Add RPC retry logic + fallback nodes
2. ✅ Configure DB connection pool properly
3. ✅ Add Telegram rate limiting
4. ✅ Store notification state in Redis

**Timeline**: 2-3 days  
**Effort**: Medium

---

### Phase 2: Week 1 of Production
1. Monitor for memory leaks
2. Watch for duplicate notifications
3. Test with 100+ concurrent users
4. Set up basic alerting

**Timeline**: 1 week  
**Effort**: Low

---

### Phase 3: Month 1
1. Implement gas price estimation
2. Handle chain reorgs gracefully
3. Add database cleanup job
4. Full monitoring dashboard

**Timeline**: 1 month  
**Effort**: High

---

## 🚀 RECOMMENDED DEPLOYMENT STRATEGY

### Step 1: Soft Launch (Week 1)
- Invite 10-20 test users
- Monitor closely for issues
- Fix critical bugs quickly

### Step 2: Limited Release (Week 2-3)
- Open to 100-200 users
- Stress test RPC and DB
- Optimize based on metrics

### Step 3: Full Launch (Week 4+)
- Remove user limits
- Scale infrastructure as needed
- Add advanced monitoring

---

## 📞 INCIDENT RESPONSE

**When bot crashes in production:**

1. Check logs: `docker-compose logs bot --tail 100`
2. Check RPC health: Try manual calls
3. Check DB connections: `SELECT count(*) FROM pg_stat_activity`
4. Restart if needed: `docker-compose restart bot`
5. Notify users on Telegram channel

**Emergency contacts:**
- RPC issues: Switch to fallback RPC
- DB issues: Scale up connection pool
- Telegram bans: Wait + reduce send rate

---

**Generated**: 2025-10-03  
**Author**: Production Readiness Analysis  
**Status**: 🟡 Requires attention before full production launch

