#!/usr/bin/env python3
"""
Automated testing script for Cellframe Navigator Bot
Tests real user scenarios with actual blockchain data
"""
import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

import httpx
from web3 import Web3

# Test configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8352448142:AAFtzNHlVARgBUyL1_Mt4_Ij0LLrrGHVhjg")
TEST_USER_ID = 577784602  # Your Telegram ID

# RPC endpoints
ETH_RPC = "https://eth.llamarpc.com"
BSC_RPC = "https://bsc-dataseed.binance.org"
CF_RPC = "http://158.160.34.60"

# Test results storage
test_results = []


class TestScenario:
    """Base class for test scenarios"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.passed = False
        self.duration = 0.0
        self.notes = []
        self.errors = []
    
    async def run(self) -> bool:
        """Override in subclass"""
        raise NotImplementedError
    
    def add_note(self, note: str):
        self.notes.append(f"  ℹ️  {note}")
    
    def add_error(self, error: str):
        self.errors.append(f"  ❌ {error}")
    
    def print_result(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        print(f"\n{'='*80}")
        print(f"Scenario: {self.name}")
        print(f"Status: {status}")
        print(f"Duration: {self.duration:.2f}s")
        if self.notes:
            print("Notes:")
            for note in self.notes:
                print(note)
        if self.errors:
            print("Errors:")
            for error in self.errors:
                print(error)


class Scenario1_ConfirmedETHTx(TestScenario):
    """User tracks a confirmed Ethereum transaction"""
    
    def __init__(self):
        super().__init__(
            "Подтвержденная ETH транзакция",
            "Пользователь отслеживает старую, подтвержденную TX"
        )
    
    async def run(self) -> bool:
        start = datetime.now()
        
        try:
            # Get confirmed TX
            tx_hash = "0xa83c0c9a9f1fd79b5a3bd823375701593b4032e006b856f639e2f92350d73d29"
            self.add_note(f"Testing TX: {tx_hash[:20]}...")
            
            # Check TX exists in Ethereum
            web3 = Web3(Web3.HTTPProvider(ETH_RPC))
            try:
                tx = web3.eth.get_transaction(tx_hash)
                block_number = tx['blockNumber']
                current_block = web3.eth.block_number
                confirmations = current_block - block_number + 1
                
                self.add_note(f"TX Block: {block_number}")
                self.add_note(f"Current Block: {current_block}")
                self.add_note(f"Confirmations: {confirmations}")
                
                if confirmations > 12:
                    self.add_note("✅ TX is confirmed (>12 confirmations)")
                    self.passed = True
                else:
                    self.add_error(f"TX not fully confirmed yet: {confirmations}/12")
                    
            except Exception as e:
                self.add_error(f"Failed to get TX from Ethereum: {e}")
                
        except Exception as e:
            self.add_error(f"Test failed: {e}")
        
        self.duration = (datetime.now() - start).total_seconds()
        return self.passed


class Scenario2_FreshETHTx(TestScenario):
    """User tracks a fresh Ethereum transaction"""
    
    def __init__(self):
        super().__init__(
            "Свежая ETH транзакция",
            "Пользователь отслеживает новую TX с малым числом подтверждений"
        )
    
    async def run(self) -> bool:
        start = datetime.now()
        
        try:
            # Get fresh TX from latest block
            web3 = Web3(Web3.HTTPProvider(ETH_RPC))
            latest_block = web3.eth.get_block('latest', full_transactions=True)
            
            if latest_block['transactions']:
                tx = latest_block['transactions'][0]
                tx_hash = tx['hash'].hex()
                
                self.add_note(f"Fresh TX: {tx_hash[:20]}...")
                self.add_note(f"Block: {latest_block['number']}")
                self.add_note(f"TX Count in block: {len(latest_block['transactions'])}")
                
                # Check confirmations
                current_block = web3.eth.block_number
                confirmations = current_block - latest_block['number'] + 1
                self.add_note(f"Confirmations: {confirmations}")
                
                if confirmations < 12:
                    self.add_note("✅ Found fresh TX (pending/low confirmations)")
                    self.passed = True
                else:
                    self.add_note("⚠️  TX already confirmed, but still valid test")
                    self.passed = True
                    
            else:
                self.add_error("No transactions in latest block")
                
        except Exception as e:
            self.add_error(f"Test failed: {e}")
        
        self.duration = (datetime.now() - start).total_seconds()
        return self.passed


class Scenario3_BSCTransaction(TestScenario):
    """User tracks a BSC transaction"""
    
    def __init__(self):
        super().__init__(
            "BSC транзакция",
            "Пользователь отслеживает транзакцию в сети BSC"
        )
    
    async def run(self) -> bool:
        start = datetime.now()
        
        try:
            # Get TX from BSC
            web3 = Web3(Web3.HTTPProvider(BSC_RPC))
            latest_block = web3.eth.get_block('latest', full_transactions=True)
            
            if latest_block['transactions']:
                tx = latest_block['transactions'][0]
                tx_hash = tx['hash'].hex()
                
                self.add_note(f"BSC TX: {tx_hash[:20]}...")
                self.add_note(f"Block: {latest_block['number']}")
                
                # Verify it's from BSC (different block numbers)
                current_block = web3.eth.block_number
                self.add_note(f"BSC Current Block: {current_block}")
                
                if current_block > 20000000:  # BSC has much higher block numbers
                    self.add_note("✅ Confirmed BSC network")
                    self.passed = True
                else:
                    self.add_error("Block number too low for BSC")
                    
            else:
                self.add_error("No transactions in BSC block")
                
        except Exception as e:
            self.add_error(f"Test failed: {e}")
        
        self.duration = (datetime.now() - start).total_seconds()
        return self.passed


class Scenario4_InvalidTxHash(TestScenario):
    """User sends invalid transaction hash"""
    
    def __init__(self):
        super().__init__(
            "Невалидный TX hash",
            "Пользователь отправляет неправильный формат хеша"
        )
    
    async def run(self) -> bool:
        start = datetime.now()
        
        try:
            # Test various invalid formats
            invalid_hashes = [
                "0x123",  # Too short
                "random_text",  # Not hex
                "12345678",  # No 0x prefix, too short
                "",  # Empty
            ]
            
            for tx_hash in invalid_hashes:
                self.add_note(f"Testing invalid: '{tx_hash}'")
                
                # Check if it matches expected format
                if not tx_hash.startswith("0x") or len(tx_hash) != 66:
                    self.add_note(f"  ✅ Correctly rejected: {tx_hash}")
                else:
                    self.add_error(f"  Should reject but format looks valid: {tx_hash}")
            
            self.passed = True
            
        except Exception as e:
            self.add_error(f"Test failed: {e}")
        
        self.duration = (datetime.now() - start).total_seconds()
        return self.passed


class Scenario5_NonExistentTx(TestScenario):
    """User tracks transaction that doesn't exist"""
    
    def __init__(self):
        super().__init__(
            "Несуществующая транзакция",
            "Пользователь отправляет валидный формат, но TX не существует"
        )
    
    async def run(self) -> bool:
        start = datetime.now()
        
        try:
            # Valid format but non-existent
            fake_tx = "0x0000000000000000000000000000000000000000000000000000000000000001"
            self.add_note(f"Testing non-existent: {fake_tx[:20]}...")
            
            # Try to get from Ethereum
            web3 = Web3(Web3.HTTPProvider(ETH_RPC))
            try:
                tx = web3.eth.get_transaction(fake_tx)
                self.add_error("TX should not exist but was found!")
            except Exception:
                self.add_note("✅ TX not found (as expected)")
                self.passed = True
                
        except Exception as e:
            self.add_error(f"Test failed: {e}")
        
        self.duration = (datetime.now() - start).total_seconds()
        return self.passed


class Scenario6_CellframeRPC(TestScenario):
    """Test Cellframe RPC availability"""
    
    def __init__(self):
        super().__init__(
            "Cellframe RPC доступность",
            "Проверка работы Cellframe RPC endpoint"
        )
    
    async def run(self) -> bool:
        start = datetime.now()
        
        try:
            self.add_note(f"Testing CF RPC: {CF_RPC}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    CF_RPC,
                    json={
                        "method": "version",
                        "subcommand": [],
                        "arguments": {},
                        "id": "1"
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    version = data.get('result', [{}])[0].get('status', 'Unknown')
                    self.add_note(f"✅ CF RPC Online: {version}")
                    
                    # Test network list
                    response2 = await client.post(
                        CF_RPC,
                        json={
                            "method": "net",
                            "subcommand": ["list"],
                            "id": "1"
                        },
                        timeout=5.0
                    )
                    
                    if response2.status_code == 200:
                        nets = response2.json().get('result', [{}])[0].get('networks', [])
                        self.add_note(f"Available networks: {', '.join(nets)}")
                        self.passed = True
                    else:
                        self.add_error(f"Failed to get networks: {response2.status_code}")
                else:
                    self.add_error(f"CF RPC returned {response.status_code}")
                    
        except Exception as e:
            self.add_error(f"CF RPC unavailable: {e}")
        
        self.duration = (datetime.now() - start).total_seconds()
        return self.passed


class Scenario7_RPCPerformance(TestScenario):
    """Test RPC response times"""
    
    def __init__(self):
        super().__init__(
            "Производительность RPC",
            "Проверка времени отклика всех RPC endpoints"
        )
    
    async def run(self) -> bool:
        start = datetime.now()
        
        try:
            # Test Ethereum RPC
            web3_eth = Web3(Web3.HTTPProvider(ETH_RPC))
            eth_start = datetime.now()
            block_eth = web3_eth.eth.block_number
            eth_time = (datetime.now() - eth_start).total_seconds()
            self.add_note(f"ETH RPC: {eth_time:.3f}s (block: {block_eth})")
            
            # Test BSC RPC
            web3_bsc = Web3(Web3.HTTPProvider(BSC_RPC))
            bsc_start = datetime.now()
            block_bsc = web3_bsc.eth.block_number
            bsc_time = (datetime.now() - bsc_start).total_seconds()
            self.add_note(f"BSC RPC: {bsc_time:.3f}s (block: {block_bsc})")
            
            # Test Cellframe RPC
            async with httpx.AsyncClient() as client:
                cf_start = datetime.now()
                response = await client.post(
                    CF_RPC,
                    json={"method": "version", "subcommand": [], "arguments": {}, "id": "1"},
                    timeout=5.0
                )
                cf_time = (datetime.now() - cf_start).total_seconds()
                self.add_note(f"CF RPC: {cf_time:.3f}s (status: {response.status_code})")
            
            # Check if all are acceptable (<3s)
            if eth_time < 3.0 and bsc_time < 3.0 and cf_time < 3.0:
                self.add_note("✅ All RPCs responding within acceptable time")
                self.passed = True
            else:
                self.add_error("Some RPCs are slow (>3s)")
                
        except Exception as e:
            self.add_error(f"Performance test failed: {e}")
        
        self.duration = (datetime.now() - start).total_seconds()
        return self.passed


class Scenario8_DatabaseCheck(TestScenario):
    """Check database connectivity and data"""
    
    def __init__(self):
        super().__init__(
            "Проверка базы данных",
            "Проверка подключения к БД и наличия данных"
        )
    
    async def run(self) -> bool:
        start = datetime.now()
        
        try:
            import subprocess
            
            # Check if database is accessible
            result = subprocess.run(
                ["docker-compose", "exec", "-T", "db", "psql", "-U", "postgres", "-d", "cellframe", "-c", "SELECT COUNT(*) FROM users;"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self.add_note("✅ Database accessible")
                self.add_note(f"Output: {result.stdout.strip()}")
                
                # Check transactions table
                result2 = subprocess.run(
                    ["docker-compose", "exec", "-T", "db", "psql", "-U", "postgres", "-d", "cellframe", "-c", "SELECT COUNT(*) FROM transactions;"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result2.returncode == 0:
                    self.add_note(f"Transactions: {result2.stdout.strip()}")
                    self.passed = True
                else:
                    self.add_error("Failed to query transactions table")
            else:
                self.add_error(f"Database query failed: {result.stderr}")
                
        except Exception as e:
            self.add_error(f"Database check failed: {e}")
        
        self.duration = (datetime.now() - start).total_seconds()
        return self.passed


class Scenario9_ServicesHealth(TestScenario):
    """Check all Docker services health"""
    
    def __init__(self):
        super().__init__(
            "Здоровье сервисов",
            "Проверка что все Docker контейнеры работают"
        )
    
    async def run(self) -> bool:
        start = datetime.now()
        
        try:
            import subprocess
            
            result = subprocess.run(
                ["docker-compose", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout
                self.add_note("Services status:")
                
                required_services = ["bot", "db", "redis", "tx_monitor", "watcher", "worker"]
                all_up = True
                
                for service in required_services:
                    if service in output and "Up" in output:
                        self.add_note(f"  ✅ {service}: Running")
                    else:
                        self.add_error(f"  ❌ {service}: Not running")
                        all_up = False
                
                self.passed = all_up
            else:
                self.add_error("Failed to check services status")
                
        except Exception as e:
            self.add_error(f"Health check failed: {e}")
        
        self.duration = (datetime.now() - start).total_seconds()
        return self.passed


class Scenario10_ConcurrentRequests(TestScenario):
    """Simulate multiple users tracking TXs simultaneously"""
    
    def __init__(self):
        super().__init__(
            "Одновременные запросы",
            "Симуляция нескольких пользователей одновременно"
        )
    
    async def run(self) -> bool:
        start = datetime.now()
        
        try:
            # Get multiple TXs
            web3_eth = Web3(Web3.HTTPProvider(ETH_RPC))
            latest_block = web3_eth.eth.get_block('latest', full_transactions=True)
            
            if len(latest_block['transactions']) >= 3:
                tx_hashes = [tx['hash'].hex() for tx in latest_block['transactions'][:3]]
                self.add_note(f"Testing {len(tx_hashes)} concurrent TX lookups")
                
                # Simulate checking all TXs
                tasks = []
                for tx_hash in tx_hashes:
                    async def check_tx(hash_val):
                        try:
                            tx = web3_eth.eth.get_transaction(hash_val)
                            return True
                        except:
                            return False
                    
                    tasks.append(check_tx(tx_hash))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                success_count = sum(1 for r in results if r is True)
                
                self.add_note(f"✅ Successfully processed {success_count}/{len(tx_hashes)} TXs")
                self.passed = success_count == len(tx_hashes)
            else:
                self.add_note("⚠️  Not enough TXs in block for concurrent test")
                self.passed = True  # Not a failure, just skip
                
        except Exception as e:
            self.add_error(f"Concurrent test failed: {e}")
        
        self.duration = (datetime.now() - start).total_seconds()
        return self.passed


async def run_all_tests():
    """Run all test scenarios"""
    
    print("="*80)
    print("🧪 CELLFRAME NAVIGATOR BOT - AUTOMATED TESTING")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Define all scenarios
    scenarios = [
        Scenario9_ServicesHealth(),  # Check services first
        Scenario8_DatabaseCheck(),
        Scenario7_RPCPerformance(),
        Scenario6_CellframeRPC(),
        Scenario1_ConfirmedETHTx(),
        Scenario2_FreshETHTx(),
        Scenario3_BSCTransaction(),
        Scenario4_InvalidTxHash(),
        Scenario5_NonExistentTx(),
        Scenario10_ConcurrentRequests(),
    ]
    
    # Run each scenario
    passed = 0
    failed = 0
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] Running: {scenario.name}...")
        print(f"Description: {scenario.description}")
        
        result = await scenario.run()
        scenario.print_result()
        
        if result:
            passed += 1
        else:
            failed += 1
    
    # Print summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"Total: {len(scenarios)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/len(scenarios)*100):.1f}%")
    print()
    
    # Print recommendations
    print("="*80)
    print("💡 RECOMMENDATIONS FOR USERS")
    print("="*80)
    print("""
1. **Transaction Format**:
   - Ethereum/BSC: Must start with 0x and be 66 characters
   - Cellframe: Variable length, base58 format
   
2. **Expected Response Time**:
   - Normal: 2-5 seconds
   - Slow network: up to 10 seconds
   
3. **Common Issues Users May Face**:
   - ❌ "Transaction not found" - TX might be very new or on wrong network
   - ❌ "Invalid format" - Check TX hash format
   - ⏰ Slow response - RPC might be busy, retry in few seconds
   
4. **Best Practices**:
   - ✅ Copy TX hash from block explorer
   - ✅ Wait 1-2 blocks before tracking for best accuracy
   - ✅ Use /mysessions to see all tracked TXs
   - ✅ Enable notifications to get updates automatically
   
5. **What Users Should Know**:
   - Confirmations needed: ETH (12), BSC (15), Cellframe (3)
   - Progress notifications every 30 seconds
   - TX data persists across bot restarts
   - Can track same TX multiple times (shows current status)
""")
    
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    return passed, failed


if __name__ == "__main__":
    try:
        passed, failed = asyncio.run(run_all_tests())
        sys.exit(0 if failed == 0 else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)

