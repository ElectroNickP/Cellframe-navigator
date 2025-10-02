# 🧪 Test Scenarios for Cellframe Navigator Bot

## 📊 Real Test Data

### 1. Ethereum Transactions (Recent, Real)

```bash
# Fresh TX from latest block
TX1_ETH=$(curl -s -X POST https://eth.llamarpc.com -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getBlockByNumber","params":["latest", true],"id":1}' | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(d['result']['transactions'][0]['hash'] if d.get('result') and d['result'].get('transactions') else '')")

echo "Ethereum TX: $TX1_ETH"
```

**Or use these confirmed transactions:**
- `0xa83c0c9a9f1fd79b5a3bd823375701593b4032e006b856f639e2f92350d73d29` (Block: 23491234) ✅
- `0xf5a0c854d25a76278eebf32fbf3e780a0bb4f657613fbfe50166afe5c5b1e806` (Recent)

### 2. BSC Transactions (Real)

```bash
# BSC latest TX
TX1_BSC=$(curl -s -X POST https://bsc-dataseed.binance.org -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getBlockByNumber","params":["latest", true],"id":1}' | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(d['result']['transactions'][0]['hash'] if d.get('result') and d['result'].get('transactions') else '')")

echo "BSC TX: $TX1_BSC"
```

### 3. Cellframe Transactions

**Get from Cellframe RPC:**
```bash
# Get recent TX from mempool or history
curl -X POST http://158.160.34.60 \
  -H "Content-Type: application/json" \
  -d '{
    "method": "mempool",
    "subcommand": ["list"],
    "arguments": {"net": "Backbone", "chain": "main"},
    "id": "1"
  }'
```

**Test addresses (Cellframe format):**
- Valid: `mYWN7Ccrqgtt9W9349Cfqg7g4m1UwAyELuZkZ5SJvCMr`
- Another: `Rj7J7MiX2bWy8sNyX38bB86KTFUnSn7sdKDsTFa2RJyQTDWFaebrj6BucT7Wa5CSq`

---

## 🎯 Test Scenarios

### Scenario 1: Basic TX Tracking (Ethereum)

**Goal:** Test basic `/track` functionality with Ethereum

**Steps:**
1. Open Telegram bot `@cefframe_bot`
2. Send: `/start`
3. Send: `/track 0xa83c0c9a9f1fd79b5a3bd823375701593b4032e006b856f639e2f92350d73d29`

**Expected Result:**
```
✅ Transaction Confirmed!

Your transaction on Ethereum has been confirmed!

TX Hash: 0xa83c0c9a...50d73d29
Confirmations: 80+/12
Block: 23491234

✨ Your tokens are safe!

Note: This transaction was already tracked.
```

**Validation:**
- ✅ Bot responds within 3 seconds
- ✅ Shows correct chain (Ethereum)
- ✅ Shows confirmation count > 12
- ✅ Shows block number
- ✅ Status is "Confirmed"

---

### Scenario 2: Fresh Transaction Tracking

**Goal:** Track a brand new transaction with 0 confirmations

**Steps:**
1. Get fresh TX hash:
   ```bash
   curl -s -X POST https://eth.llamarpc.com -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_getBlockByNumber","params":["latest", true],"id":1}' | \
     python3 -c "import sys, json; d=json.load(sys.stdin); txs=d['result']['transactions']; print(txs[0]['hash'])"
   ```

2. Send to bot: `/track <fresh_tx_hash>`

**Expected Result:**
```
⏳ Transaction Tracked!

Chain: Ethereum
TX Hash: 0x...
Status: Pending ⏳
Confirmations: 0/12
Block: 23491500

⏱ Estimated time: ~180 seconds

I'll notify you when this transaction is confirmed!
```

**Validation:**
- ✅ Status is "Pending"
- ✅ Confirmations are low (0-5)
- ✅ Bot promises notification
- ⏰ Wait 5 minutes → should receive progress update

---

### Scenario 3: Multi-Chain Auto-Detection

**Goal:** Test automatic chain detection

**Test Cases:**

#### 3a. Ethereum (0x prefix, 66 chars)
```
/track 0xa83c0c9a9f1fd79b5a3bd823375701593b4032e006b856f639e2f92350d73d29
Expected: "Chain: Ethereum" ✅
```

#### 3b. BSC (same format, different TX)
```
/track <bsc_tx_hash>
Expected: "Chain: BSC" ✅
```

#### 3c. Cellframe (base58 format)
```
/track mYWN7Ccrqgtt9W9349Cfqg7g4m1UwAyELuZkZ5SJvCMr
Expected: "Chain: Cellframe" ✅
```

**Validation:**
- ✅ Bot correctly identifies each chain
- ✅ Shows appropriate confirmation requirements (ETH:12, BSC:15, CF:3)

---

### Scenario 4: Duplicate Tracking

**Goal:** Test behavior when tracking same TX twice

**Steps:**
1. Track TX: `/track 0xa83c0c9a...`
2. Wait for response
3. Track same TX again: `/track 0xa83c0c9a...`

**Expected Result (2nd time):**
```
✅ Transaction Confirmed!

...

Note: This transaction was already tracked.
```

**Validation:**
- ✅ Shows current status (not old cached data)
- ✅ Mentions "already tracked"
- ✅ Confirmation count is updated
- ✅ No duplicate entries in database

---

### Scenario 5: Invalid TX Hash

**Goal:** Test error handling

**Test Cases:**

#### 5a. Too short
```
/track 0x123
Expected: ❌ Invalid transaction hash format
```

#### 5b. Wrong format
```
/track random_text_12345
Expected: ❌ Invalid transaction hash format
```

#### 5c. Valid format but doesn't exist
```
/track 0x0000000000000000000000000000000000000000000000000000000000000000
Expected: ❌ Transaction not found
```

**Validation:**
- ✅ Clear error messages
- ✅ Helpful instructions
- ✅ No crash or hang

---

### Scenario 6: Push Notifications

**Goal:** Test automatic progress notifications

**Steps:**
1. Find a pending TX (0-3 confirmations)
2. Track it: `/track <pending_tx>`
3. Wait 30-60 seconds

**Expected Timeline:**
```
T+0s:   ⏳ Transaction Tracked! (0/12)
T+30s:  �� Transaction Progress (3/12) - 25%
T+60s:  🔄 Transaction Progress (6/12) - 50%
T+90s:  🔄 Transaction Progress (9/12) - 75%
T+120s: ✅ Transaction Confirmed! (12/12)
```

**Validation:**
- ✅ Progress notifications arrive every 30s
- ✅ Progress bar displays correctly
- ✅ Final confirmation notification
- ✅ "Your tokens are safe!" message

---

### Scenario 7: Multiple Simultaneous Tracking

**Goal:** Test tracking multiple TX at once

**Steps:**
1. Track ETH TX: `/track <eth_tx>`
2. Track BSC TX: `/track <bsc_tx>`
3. Track CF TX: `/track <cf_tx>`
4. Check sessions: `/mysessions`

**Expected Result:**
```
📚 Your Bridge Sessions

1. ⏳ CELL 100
   Direction: Eth → Cf
   Status: pending
   ID: xxx

2. ⏳ CELL 50
   Direction: Bsc → Cf
   Status: pending
   ID: yyy

3. ⏳ CELL 25
   Direction: Cellframe → Eth
   Status: pending
   ID: zzz
```

**Validation:**
- ✅ All 3 TX tracked independently
- ✅ Each shows correct chain
- ✅ `/mysessions` lists all
- ✅ Notifications work for each

---

### Scenario 8: Database Persistence

**Goal:** Test that data survives bot restart

**Steps:**
1. Track a TX: `/track <tx_hash>`
2. Note the Session ID
3. Restart bot: `docker-compose restart bot`
4. Check: `/mysessions`

**Expected Result:**
- ✅ Session still exists
- ✅ TX data preserved
- ✅ Status updated from blockchain
- ✅ No data loss

---

### Scenario 9: Bridge Flow Integration

**Goal:** Test full bridge creation workflow

**Steps:**
1. `/bridge`
2. Select: "Ethereum → Cellframe"
3. Select token: "CELL"
4. Enter source address: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1`
5. Enter destination address: `mYWN7Ccrqgtt9W9349Cfqg7g4m1UwAyELuZkZ5SJvCMr`
6. Enter amount: `100`
7. Confirm

**Expected Result:**
```
✅ Bridge Session Created!

Session ID: xxx
Direction: Ethereum → Cellframe
Amount: 100 CELL
...
```

**Validation:**
- ✅ FSM flow works smoothly
- ✅ Address validation works
- ✅ Session saved to database
- ✅ Shows CFSCAN link

---

### Scenario 10: Stress Test

**Goal:** Test bot under load

**Steps:**
1. Open 3 separate Telegram clients
2. Each sends 5 `/track` commands rapidly
3. Monitor bot performance

**Expected Result:**
- ✅ All requests handled (no drops)
- ✅ Response time < 5 seconds per request
- ✅ No errors in logs
- ✅ Database handles concurrent writes
- ✅ TX Monitor continues working

---

## 🔧 Monitoring During Tests

### Check Logs:
```bash
# Bot logs
docker-compose logs -f bot

# TX Monitor logs
docker-compose logs -f tx_monitor

# All services
docker-compose logs -f
```

### Check Database:
```bash
# See tracked transactions
docker-compose exec -T db psql -U postgres -d cellframe -c \
  "SELECT hash, chain, confirmations, status FROM transactions ORDER BY created_at DESC LIMIT 5;"

# See users
docker-compose exec -T db psql -U postgres -d cellframe -c \
  "SELECT id, username, created_at FROM users;"

# See sessions
docker-compose exec -T db psql -U postgres -d cellframe -c \
  "SELECT session_id, direction, token, amount, status FROM bridge_sessions ORDER BY created_at DESC LIMIT 5;"
```

### Check Services Health:
```bash
docker-compose ps
docker-compose logs --tail 20 tx_monitor
```

---

## ✅ Success Criteria

### Must Pass:
- [ ] Scenarios 1-5 (Basic functionality)
- [ ] Scenario 6 (Push notifications)
- [ ] Scenario 8 (Data persistence)

### Nice to Have:
- [ ] Scenario 7 (Multi-TX tracking)
- [ ] Scenario 9 (Bridge flow)
- [ ] Scenario 10 (Stress test)

---

## 🐛 Known Issues to Test

1. **Network timeout:** What happens if RPC is slow?
2. **Invalid Cellframe TX format:** Does it fallback gracefully?
3. **Very old TX (1000+ confirmations):** Does it still work?
4. **Mempool TX (0 confirmations):** Progress updates work?

---

## 📊 Test Results Template

```markdown
## Test Run: YYYY-MM-DD HH:MM

### Environment:
- Bot Version: <git commit>
- Networks: ETH ✅ BSC ✅ CF ✅
- Services: All Up ✅

### Results:
| Scenario | Status | Notes |
|----------|--------|-------|
| 1. Basic ETH tracking | ✅ PASS | Response in 2.1s |
| 2. Fresh TX | ✅ PASS | Notification received |
| 3. Auto-detection | ✅ PASS | All 3 chains OK |
| ... | ... | ... |

### Issues Found:
1. None

### Performance:
- Average response time: 2.5s
- Notification delay: 30-35s
- Database queries: Fast (<100ms)

### Conclusion:
✅ All tests passed. System is production-ready!
```

---

## 🚀 Ready to Test!

**Start with:**
```
Scenario 1 → Scenario 2 → Scenario 6
```

These cover the core functionality. Let me know results! 📊
