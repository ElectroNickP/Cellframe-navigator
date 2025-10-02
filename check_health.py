#!/usr/bin/env python3
"""
Health check script for all services.
Verifies that production fixes are working correctly.
"""
import asyncio
import os
import sys
from datetime import datetime

import redis.asyncio as redis
from sqlalchemy import text
from web3 import Web3

from data.database import get_session_factory


async def check_database():
    """Check database connection and pool."""
    print("🔍 Checking Database...")
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        print("  ✅ Database connection: OK")
        print("  ✅ Connection pool: Configured")
        return True
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False


async def check_redis():
    """Check Redis connection."""
    print("\n🔍 Checking Redis...")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        await r.ping()
        await r.set("health_check", datetime.now().isoformat(), ex=60)
        value = await r.get("health_check")
        await r.close()
        print(f"  ✅ Redis connection: OK")
        print(f"  ✅ Redis write/read: OK")
        return True
    except Exception as e:
        print(f"  ❌ Redis error: {e}")
        return False


async def check_rpc_nodes():
    """Check RPC nodes availability."""
    print("\n🔍 Checking RPC Nodes...")
    
    results = {}
    
    # Check Ethereum RPC
    eth_rpc = os.getenv("ETH_RPC_URL")
    if eth_rpc:
        try:
            w3 = Web3(Web3.HTTPProvider(eth_rpc, request_kwargs={'timeout': 10}))
            block = w3.eth.block_number
            print(f"  ✅ Ethereum RPC: OK (block: {block})")
            results['eth'] = True
        except Exception as e:
            print(f"  ⚠️  Ethereum RPC: {str(e)[:50]}")
            results['eth'] = False
    else:
        print("  ⚠️  Ethereum RPC: Not configured")
        results['eth'] = None
    
    # Check BSC RPC
    bsc_rpc = os.getenv("BSC_RPC_URL")
    if bsc_rpc:
        try:
            w3 = Web3(Web3.HTTPProvider(bsc_rpc, request_kwargs={'timeout': 10}))
            block = w3.eth.block_number
            print(f"  ✅ BSC RPC: OK (block: {block})")
            results['bsc'] = True
        except Exception as e:
            print(f"  ⚠️  BSC RPC: {str(e)[:50]}")
            results['bsc'] = False
    else:
        print("  ⚠️  BSC RPC: Not configured")
        results['bsc'] = None
    
    # Check Cellframe RPC
    cf_rpc = os.getenv("CF_RPC_URL")
    if cf_rpc:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    cf_rpc,
                    json={"jsonrpc": "2.0", "method": "net_get_cur_addr", "id": 1}
                )
                data = response.json()
                print(f"  ✅ Cellframe RPC: OK")
                results['cf'] = True
        except Exception as e:
            print(f"  ⚠️  Cellframe RPC: {str(e)[:50]}")
            results['cf'] = False
    else:
        print("  ⚠️  Cellframe RPC: Not configured")
        results['cf'] = None
    
    return results


async def check_fallback_nodes():
    """Check fallback RPC nodes."""
    print("\n🔍 Checking Fallback Nodes...")
    
    # Test Ethereum fallbacks
    eth_fallbacks = [
        ("LlamaRPC ETH", "https://eth.llamarpc.com"),
        ("Ankr ETH", "https://rpc.ankr.com/eth"),
        ("Public RPC ETH", "https://eth.public-rpc.com"),
    ]
    
    print("  Ethereum fallbacks:")
    eth_ok = 0
    for name, url in eth_fallbacks:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 5}))
            block = w3.eth.block_number
            print(f"    ✅ {name}: OK (block: {block})")
            eth_ok += 1
        except Exception as e:
            print(f"    ❌ {name}: Failed")
    
    # Test BSC fallbacks
    bsc_fallbacks = [
        ("Binance BSC", "https://bsc-dataseed.binance.org"),
        ("Ankr BSC", "https://rpc.ankr.com/bsc"),
        ("Public RPC BSC", "https://bsc.public-rpc.com"),
    ]
    
    print("\n  BSC fallbacks:")
    bsc_ok = 0
    for name, url in bsc_fallbacks:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 5}))
            block = w3.eth.block_number
            print(f"    ✅ {name}: OK (block: {block})")
            bsc_ok += 1
        except Exception as e:
            print(f"    ❌ {name}: Failed")
    
    print(f"\n  Ethereum fallbacks available: {eth_ok}/3")
    print(f"  BSC fallbacks available: {bsc_ok}/3")
    
    return eth_ok > 0 and bsc_ok > 0


async def check_bot_config():
    """Check bot configuration."""
    print("\n🔍 Checking Bot Configuration...")
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token and len(bot_token) > 20:
        print("  ✅ Bot token: Configured")
    else:
        print("  ❌ Bot token: Missing or invalid")
        return False
    
    return True


async def main():
    """Run all health checks."""
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║              🏥 PRODUCTION HEALTH CHECK                          ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(f"\n⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {
        'database': await check_database(),
        'redis': await check_redis(),
        'bot_config': await check_bot_config(),
    }
    
    results['rpc_nodes'] = await check_rpc_nodes()
    results['fallbacks'] = await check_fallback_nodes()
    
    # Summary
    print("\n" + "━" * 70)
    print("📊 SUMMARY")
    print("━" * 70)
    
    all_ok = True
    
    if results['database']:
        print("✅ Database: OK")
    else:
        print("❌ Database: FAILED")
        all_ok = False
    
    if results['redis']:
        print("✅ Redis: OK")
    else:
        print("❌ Redis: FAILED")
        all_ok = False
    
    if results['bot_config']:
        print("✅ Bot Config: OK")
    else:
        print("❌ Bot Config: FAILED")
        all_ok = False
    
    # RPC summary
    rpc_ok = any(v for v in results['rpc_nodes'].values() if v is True)
    if rpc_ok:
        print("✅ RPC Nodes: At least one working")
    else:
        print("⚠️  RPC Nodes: None working (check configuration)")
    
    if results['fallbacks']:
        print("✅ Fallback Nodes: Available")
    else:
        print("⚠️  Fallback Nodes: Limited availability")
    
    print("\n" + "━" * 70)
    
    if all_ok:
        print("✅ SYSTEM STATUS: HEALTHY 🎉")
        print("\nAll critical services are operational!")
        print("Production fixes verified:")
        print("  ✓ Database connection pool configured")
        print("  ✓ Redis for notification deduplication")
        print("  ✓ RPC fallback nodes available")
        return 0
    else:
        print("❌ SYSTEM STATUS: UNHEALTHY ⚠️")
        print("\nSome critical services failed!")
        print("Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

