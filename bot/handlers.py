"""
Improved bot handlers with address validation, fee estimation, and better UX.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards import (
    action_keyboard,
    confirmation_keyboard,
    direction_keyboard,
    get_chain_name,
    parse_direction,
    token_keyboard,
)
from bot.status_handler import StatusCommandHandler
from bot.storage import BindingStorage
from data.database import get_session_factory
from data.repositories import BridgeSessionRepository, TransactionRepository, UserRepository
from watcher.cfscan import CFSCANIntegration
from watcher.evm_tracker import EVMTransactionTracker
from watcher.validators import validate_address


logger = logging.getLogger(__name__)

# Initialize services
status_handler = StatusCommandHandler()
cfscan = CFSCANIntegration()

# Get database session factory
SessionFactory = get_session_factory()


class BridgeFlow(StatesGroup):
    """States for bridge creation flow."""
    choosing_direction = State()
    choosing_token = State()
    entering_src_address = State()
    entering_dst_address = State()
    entering_amount = State()
    confirming = State()


class BindFlow(StatesGroup):
    """States for address binding flow."""
    waiting_chain = State()
    waiting_address = State()


binding_storage = BindingStorage()


def register_handlers(dp: Router) -> None:
    """Register all bot handlers."""
    router = Router()

    # ==================== Command Handlers ====================

    @router.message(Command("start", "help"))
    async def cmd_help(message: types.Message) -> None:
        """Show help message with available commands."""
        help_text = (
            "🌉 <b>Cellframe Bridge Navigator</b>\n\n"
            "Monitor and track your cross-chain bridge transactions between "
            "Ethereum, BSC, and Cellframe networks.\n\n"
            "<b>Available Commands:</b>\n"
            "/bridge - Start new bridge session\n"
            "/track <tx_hash> - Track transaction in real-time 🔥\n"
            "/status [tx_hash] - Check transaction status\n"
            "/mysessions - View your bridge sessions\n"
            "/fees - View current bridge fees\n"
            "/bind - Link your blockchain addresses\n"
            "/help - Show this message\n\n"
            "<b>Supported Networks:</b>\n"
            "• Ethereum (ERC-20)\n"
            "• BSC (BEP-20)\n"
            "• Cellframe (CF-20)\n\n"
            "<i>Note: Always double-check addresses before bridging!</i>"
        )
        await message.answer(help_text)

    @router.message(Command("bridge"))
    async def cmd_bridge(message: types.Message, state: FSMContext) -> None:
        """Start bridge creation flow."""
        await state.clear()
        await state.set_state(BridgeFlow.choosing_direction)
        
        intro_text = (
            "🌉 <b>Create New Bridge Session</b>\n\n"
            "Choose the direction for your bridge transaction:\n\n"
            "<i>Tip: Make sure you have the latest Cellframe Wallet/Dashboard version!</i>"
        )
        
        await message.answer(intro_text, reply_markup=direction_keyboard())

    @router.message(Command("status"))
    async def cmd_status(message: types.Message) -> None:
        """Check transaction status with smart diagnostics."""
        # Parse tx hash if provided
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            tx_hash = parts[1].strip()
            await status_handler.handle_status_command(message, tx_hash)
        else:
            # Show user's sessions
            await status_handler.handle_status_command(message)

    @router.message(Command("fees"))
    async def cmd_fees(message: types.Message) -> None:
        """Show current bridge fees."""
        fees_text = (
            "💰 <b>Current Bridge Fees</b>\n\n"
            "<b>Ethereum ⇄ Cellframe:</b>\n"
            "• ETH gas: ~0.003-0.01 ETH (varies)\n"
            "• CF-20 fee: ~0.0001 CELL\n"
            "• Est. time: ~5-10 minutes\n\n"
            "<b>BSC ⇄ Cellframe:</b>\n"
            "• BNB gas: ~0.0003-0.001 BNB\n"
            "• CF-20 fee: ~0.0001 CELL\n"
            "• Est. time: ~3-7 minutes\n\n"
            "<i>Fees are estimated and may vary based on network congestion.\n"
            "Use /bridge to get real-time estimates.</i>"
        )
        await message.answer(fees_text)

    @router.message(Command("bind"))
    async def cmd_bind(message: types.Message, state: FSMContext) -> None:
        """Start address binding flow."""
        await state.clear()
        await state.set_state(BindFlow.waiting_chain)
        
        bind_text = (
            "🔗 <b>Bind Blockchain Address</b>\n\n"
            "Choose the network and send your address:\n\n"
            "<b>Format:</b> <code>NETWORK:address</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>ETH:0x742d35Cc6...</code>\n"
            "• <code>BSC:0x742d35Cc6...</code>\n"
            "• <code>CF20:your_cf20_address</code>\n\n"
            "Send /cancel to abort"
        )
        await message.answer(bind_text)

    @router.message(Command("mysessions"))
    async def cmd_my_sessions(message: types.Message) -> None:
        """Show user's bridge sessions."""
        try:
            async with SessionFactory() as db_session:
                user_repo = UserRepository(db_session)
                user = await user_repo.get_or_create(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                )
                
                session_repo = BridgeSessionRepository(db_session)
                sessions = await session_repo.list_by_user(user.id, limit=10)
                
                if not sessions:
                    await message.answer(
                        "You don't have any bridge sessions yet.\n"
                        "Use /bridge to create one!"
                    )
                    return

                response = "📚 <b>Your Bridge Sessions</b>\n\n"
                for idx, session in enumerate(sessions, 1):
                    status_emoji = {
                        "pending": "⏳",
                        "processing": "🔄",
                        "completed": "✅",
                        "failed": "❌",
                    }.get(session.status, "❓")
                    
                    direction_display = session.direction.replace('_to_', ' → ').replace('_', ' ').title()
                    
                    response += (
                        f"{idx}. {status_emoji} <b>{session.token}</b> {session.amount}\n"
                        f"   Direction: {direction_display}\n"
                        f"   Status: {session.status}\n"
                        f"   ID: <code>{session.session_id}</code>\n\n"
                    )
                
                await message.answer(response)
                
        except Exception as e:
            logger.error(f"Failed to fetch sessions: {e}", exc_info=True)
            await message.answer(
                "❌ Failed to fetch your sessions.\n"
                "Please try again later."
            )

    @router.message(Command("track"))
    async def cmd_track(message: types.Message) -> None:
        """Track a transaction by hash."""
        # Extract TX hash from message
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer(
                "📍 <b>Track Transaction</b>\n\n"
                "Send me a transaction hash to track:\n\n"
                "<b>Usage:</b> <code>/track 0x123...</code>\n\n"
                "<b>Supported:</b>\n"
                "• Ethereum TX hash\n"
                "• BSC TX hash\n"
                "• Cellframe TX hash"
            )
            return
        
        tx_hash = parts[1].strip()
        
        # Validate TX hash format and detect chain
        is_evm = False
        is_cellframe = False
        
        if tx_hash.startswith("0x") and len(tx_hash) == 66:
            # Ethereum/BSC format
            is_evm = True
        elif len(tx_hash) == 64:
            # Could be Cellframe or Ethereum without 0x
            # Try to detect: Cellframe hashes are usually base58 or hex
            if not tx_hash.startswith("0x"):
                # Check if it looks like Cellframe (contains base58 chars)
                if any(c in tx_hash for c in "ghijklmnopqrstuvwxyzGHIJKLMNOPQRSTUVWXYZ"):
                    is_cellframe = True
                else:
                    # Probably Ethereum without 0x
                    tx_hash = "0x" + tx_hash
                    is_evm = True
            else:
                is_evm = True
        elif len(tx_hash) > 40:  # Cellframe TX hashes can be variable length
            is_cellframe = True
        else:
            await message.answer(
                "❌ Invalid transaction hash format.\n\n"
                "Please provide a valid TX hash:\n"
                "• Ethereum: 0x1234... (66 chars)\n"
                "• BSC: 0x1234... (66 chars)\n"
                "• Cellframe: base58 string"
            )
            return
        
        await message.answer("🔍 Checking transaction...")
        
        try:
            # Check if we have RPC configured
            eth_rpc = os.getenv("ETH_RPC_URL")
            bsc_rpc = os.getenv("BSC_RPC_URL")
            cf_rpc = os.getenv("CF_RPC_URL")
            
            if not eth_rpc and not bsc_rpc and not cf_rpc:
                await message.answer(
                    "⚠️ <b>RPC not configured</b>\n\n"
                    "Transaction tracking requires blockchain RPC endpoints.\n"
                    "Please configure ETH_RPC_URL, BSC_RPC_URL, or CF_RPC_URL."
                )
                return
            
            # Try to find transaction
            tracker = None
            tx_info = None
            detected_chain = None
            
            # If looks like Cellframe, try CF first
            if is_cellframe and cf_rpc:
                try:
                    from watcher.cf20_rpc import CF20RPCClient
                    cf_network = os.getenv("CF_NETWORK", "Backbone")
                    cf_client = CF20RPCClient(cf_rpc, cf_network)
                    
                    # Check transaction status
                    tx_status = await cf_client.tx_status(tx_hash)
                    
                    if tx_status and tx_status.get("found"):
                        detected_chain = "cellframe"
                        tx_info = {
                            "exists": True,
                            "confirmed": tx_status.get("status") == "accepted",
                            "confirmations": tx_status.get("confirmations", 0),
                            "block_number": tx_status.get("block"),
                            "from": tx_status.get("source_addr"),
                            "to": tx_status.get("dest_addr"),
                            "amount": tx_status.get("value"),
                        }
                        logger.info(f"Found TX on Cellframe: {tx_hash}")
                except Exception as e:
                    logger.debug(f"Not found on Cellframe: {e}")
            
            # Try EVM chains if not found or looks like EVM
            if not detected_chain and is_evm:
                # Try Ethereum first
                if eth_rpc:
                    try:
                        from web3 import Web3
                        web3_eth = Web3(Web3.HTTPProvider(eth_rpc))
                        tracker = EVMTransactionTracker(web3_eth, confirmations_required=12)
                        tx_info = await tracker.get_transaction_status(tx_hash)
                        if tx_info and tx_info.get("exists"):
                            detected_chain = "ethereum"
                    except Exception as e:
                        logger.debug(f"Not found on Ethereum: {e}")
                
                # Try BSC if not found on Ethereum
                if not detected_chain and bsc_rpc:
                    try:
                        from web3 import Web3
                        web3_bsc = Web3(Web3.HTTPProvider(bsc_rpc))
                        tracker = EVMTransactionTracker(web3_bsc, confirmations_required=15)
                        tx_info = await tracker.get_transaction_status(tx_hash)
                        if tx_info and tx_info.get("exists"):
                            detected_chain = "bsc"
                    except Exception as e:
                        logger.debug(f"Not found on BSC: {e}")
            
            if not detected_chain or not tx_info:
                await message.answer(
                    "❌ <b>Transaction not found</b>\n\n"
                    f"TX Hash: <code>{tx_hash[:20]}...{tx_hash[-10:]}</code>\n\n"
                    "This transaction was not found on Ethereum, BSC, or Cellframe.\n"
                    "Please check:\n"
                    "• TX hash is correct\n"
                    "• Transaction has been broadcasted\n"
                    "• Using the right network\n"
                    "• RPC endpoint is configured and working"
                )
                return
            
            # Save to database
            async with SessionFactory() as db_session:
                user_repo = UserRepository(db_session)
                user = await user_repo.get_or_create(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                )
                
                # Create or get session
                session_repo = BridgeSessionRepository(db_session)
                sessions = await session_repo.list_by_user(user.id, limit=1)
                
                if sessions:
                    session = sessions[0]
                else:
                    # Create a tracking-only session
                    session = await session_repo.create(
                        user_id=user.id,
                        direction=f"{detected_chain}_to_cf",
                        token="CELL",
                        amount=tx_info.get("amount", "0"),
                        src_network=detected_chain.title(),
                        dst_network="Cellframe CF-20",
                    )
                
                # Add or update transaction
                tx_repo = TransactionRepository(db_session)
                existing_tx = await tx_repo.get_by_hash(tx_hash)
                
                if not existing_tx:
                    # Set confirmations_required based on chain
                    if detected_chain == "ethereum":
                        conf_required = 12
                    elif detected_chain == "bsc":
                        conf_required = 15
                    else:  # cellframe
                        conf_required = int(os.getenv("CF_CONFIRMATIONS_REQUIRED", "3"))
                    
                    tx = await tx_repo.create(
                        session_id=session.id,
                        chain=detected_chain,
                        tx_hash=tx_hash,
                        confirmations_required=conf_required,
                        from_address=tx_info.get("from"),
                        to_address=tx_info.get("to"),
                    )
                    logger.info(f"Started tracking TX {tx_hash} for user {message.from_user.id}")
                else:
                    logger.info(f"TX {tx_hash} already tracked, showing current status")
                
                # Always update with current status (for both new and existing TX)
                await tx_repo.update_status(
                    tx_hash=tx_hash,
                    confirmations=tx_info.get("confirmations", 0),
                    block_number=tx_info.get("block_number"),
                    status="confirmed" if tx_info.get("confirmed") else "pending",
                )
                
                await db_session.commit()
                
            # Display status
            confirmations = tx_info.get("confirmations", 0)
            
            # Set required confirmations based on chain
            if detected_chain == "ethereum":
                required = 12
                chain_name = "Ethereum"
            elif detected_chain == "bsc":
                required = 15
                chain_name = "BSC"
            else:  # cellframe
                required = int(os.getenv("CF_CONFIRMATIONS_REQUIRED", "3"))
                chain_name = "Cellframe"
            
            confirmed = tx_info.get("confirmed", False)
            status_emoji = "✅" if confirmed else "⏳"
            
            # Check if already tracking
            already_tracked = existing_tx is not None
            
            if confirmed:
                status_text = (
                    f"✅ <b>Transaction Confirmed!</b>\n\n"
                    f"Your transaction on {chain_name} has been confirmed!\n\n"
                    f"<b>TX Hash:</b> <code>{tx_hash[:10]}...{tx_hash[-8:]}</code>\n"
                    f"<b>Confirmations:</b> {confirmations}/{required}\n"
                    f"<b>Block:</b> {tx_info.get('block_number')}\n\n"
                    f"✨ Your tokens are safe!"
                )
                if already_tracked:
                    status_text += "\n\n<i>Note: This transaction was already tracked.</i>"
            else:
                status_text = (
                    f"{status_emoji} <b>Transaction Tracked!</b>\n\n"
                    f"<b>Chain:</b> {chain_name}\n"
                    f"<b>TX Hash:</b> <code>{tx_hash[:10]}...{tx_hash[-8:]}</code>\n"
                    f"<b>Status:</b> Pending ⏳\n"
                    f"<b>Confirmations:</b> {confirmations}/{required}\n"
                )
                
                if tx_info.get("block_number"):
                    status_text += f"<b>Block:</b> {tx_info['block_number']}\n"
                
                status_text += (
                    f"\n⏱ <b>Estimated time:</b> ~{(required - confirmations) * 15} seconds\n\n"
                )
                
                if already_tracked:
                    status_text += "I'm already monitoring this transaction and will notify you when confirmed!"
                else:
                    status_text += "I'll notify you when this transaction is confirmed!"
            
            await message.answer(status_text)
            
        except Exception as e:
            logger.error(f"Error tracking transaction: {e}", exc_info=True)
            await message.answer(
                "❌ <b>Error tracking transaction</b>\n\n"
                "An error occurred while checking the transaction.\n"
                f"Error: {str(e)}"
            )

    @router.message(Command("cancel"))
    async def cmd_cancel(message: types.Message, state: FSMContext) -> None:
        """Cancel current operation."""
        await state.clear()
        await message.answer("❌ Operation cancelled.")

    # ==================== Bridge Flow Handlers ====================

    @router.callback_query(F.data.startswith("dir:"), BridgeFlow.choosing_direction)
    async def choose_direction(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Handle bridge direction selection."""
        direction = callback.data.split(":", 1)[1]
        await state.update_data(direction=direction)
        await state.set_state(BridgeFlow.choosing_token)
        
        src, dst = parse_direction(direction)
        
        text = (
            f"✅ Direction: <b>{get_chain_name(src)} → {get_chain_name(dst)}</b>\n\n"
            f"Now choose the token you want to bridge:"
        )
        
        await callback.message.edit_text(text, reply_markup=token_keyboard(direction))
        await callback.answer()

    @router.callback_query(F.data.startswith("token:"), BridgeFlow.choosing_token)
    async def choose_token(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Handle token selection."""
        token = callback.data.split(":", 1)[1]
        await state.update_data(token=token)
        await state.set_state(BridgeFlow.entering_src_address)
        
        data = await state.get_data()
        direction = data.get("direction", "")
        src, dst = parse_direction(direction)
        
        text = (
            f"✅ Token: <b>{token}</b>\n\n"
            f"Enter your <b>{get_chain_name(src)}</b> address:\n\n"
            f"<i>This is the address you'll send tokens FROM.</i>\n"
            f"Make sure it's correct!"
        )
        
        await callback.message.edit_text(text)
        await callback.answer()

    @router.message(BridgeFlow.entering_src_address)
    async def enter_src_address(message: types.Message, state: FSMContext) -> None:
        """Handle source address input."""
        address = message.text.strip()
        data = await state.get_data()
        direction = data.get("direction", "")
        src, _ = parse_direction(direction)
        
        # Validate address
        chain_map = {"eth": "ethereum", "bsc": "bsc", "cf": "cf20"}
        chain_type = chain_map.get(src, src)
        
        if not validate_address(address, chain_type):
            await message.answer(
                f"❌ Invalid {get_chain_name(src)} address format.\n"
                f"Please check and try again:"
            )
            return
        
        await state.update_data(src_address=address)
        await state.set_state(BridgeFlow.entering_dst_address)
        
        _, dst = parse_direction(direction)
        
        text = (
            f"✅ Source address saved!\n\n"
            f"Now enter your <b>{get_chain_name(dst)}</b> address:\n\n"
            f"<i>This is where you'll RECEIVE the tokens.</i>"
        )
        
        await message.answer(text)

    @router.message(BridgeFlow.entering_dst_address)
    async def enter_dst_address(message: types.Message, state: FSMContext) -> None:
        """Handle destination address input."""
        address = message.text.strip()
        data = await state.get_data()
        direction = data.get("direction", "")
        _, dst = parse_direction(direction)
        
        # Validate address
        chain_map = {"eth": "ethereum", "bsc": "bsc", "cf": "cf20"}
        chain_type = chain_map.get(dst, dst)
        
        if not validate_address(address, chain_type):
            await message.answer(
                f"❌ Invalid {get_chain_name(dst)} address format.\n"
                f"Please check and try again:"
            )
            return
        
        await state.update_data(dst_address=address)
        await state.set_state(BridgeFlow.entering_amount)
        
        token = data.get("token", "")
        text = (
            f"✅ Destination address saved!\n\n"
            f"Enter the amount of <b>{token}</b> to bridge:\n\n"
            f"<i>Example: 100.5</i>"
        )
        
        await message.answer(text)

    @router.message(BridgeFlow.entering_amount, F.text.regexp(r"^[0-9]*\.?[0-9]+$"))
    async def enter_amount(message: types.Message, state: FSMContext) -> None:
        """Handle amount input."""
        amount = message.text.strip()
        await state.update_data(amount=amount)
        await state.set_state(BridgeFlow.confirming)
        
        data = await state.get_data()
        direction = data.get("direction", "")
        token = data.get("token", "")
        src_address = data.get("src_address", "")
        dst_address = data.get("dst_address", "")
        src, dst = parse_direction(direction)
        
        # Format confirmation message
        confirmation_text = (
            "📋 <b>Bridge Session Summary</b>\n\n"
            f"<b>Direction:</b> {get_chain_name(src)} → {get_chain_name(dst)}\n"
            f"<b>Token:</b> {token}\n"
            f"<b>Amount:</b> {amount}\n\n"
            f"<b>From:</b> <code>{src_address[:10]}...{src_address[-8:]}</code>\n"
            f"<b>To:</b> <code>{dst_address[:10]}...{dst_address[-8:]}</code>\n\n"
            f"<i>⚠️ Please verify all details carefully!</i>\n\n"
            f"Confirm to create bridge session?"
        )
        
        await message.answer(confirmation_text, reply_markup=confirmation_keyboard())

    @router.message(BridgeFlow.entering_amount)
    async def invalid_amount(message: types.Message) -> None:
        """Handle invalid amount input."""
        await message.answer(
            "❌ Invalid amount format.\n"
            "Please enter a valid number (e.g., 100 or 100.5):"
        )

    @router.callback_query(F.data.startswith("confirm:"), BridgeFlow.confirming)
    async def handle_confirmation(callback: types.CallbackQuery, state: FSMContext) -> None:
        """Handle bridge session confirmation."""
        action = callback.data.split(":", 1)[1]
        
        if action == "no":
            await state.clear()
            await callback.message.edit_text("❌ Bridge session cancelled.")
            await callback.answer()
            return
        
        # Get session data
        data = await state.get_data()
        direction = data.get("direction", "")
        src, dst = parse_direction(direction)
        
        # Create session in database
        try:
            async with SessionFactory() as db_session:
                # Get or create user
                user_repo = UserRepository(db_session)
                user = await user_repo.get_or_create(
                    telegram_id=callback.from_user.id,
                    username=callback.from_user.username,
                )
                
                # Create bridge session
                session_repo = BridgeSessionRepository(db_session)
                session = await session_repo.create(
                    user_id=user.id,
                    direction=direction,
                    token=data.get("token", "CELL"),
                    amount=data.get("amount", "0"),
                    src_address=data.get("src_address", ""),
                    dst_address=data.get("dst_address", ""),
                    src_network=get_chain_name(src),
                    dst_network=get_chain_name(dst),
                )
                
                await db_session.commit()
                
                session_id = session.session_id
                
                logger.info(f"Created bridge session {session_id} for user {callback.from_user.id}")
                
        except Exception as e:
            logger.error(f"Failed to create bridge session: {e}", exc_info=True)
            await callback.message.edit_text(
                "❌ <b>Error creating session</b>\n\n"
                "Please try again later or contact support."
            )
            await callback.answer("Error!")
            await state.clear()
            return
        
        await state.clear()
        
        success_text = (
            "✅ <b>Bridge Session Created!</b>\n\n"
            f"Session ID: <code>{session_id}</code>\n\n"
            f"<b>Next Steps:</b>\n"
            f"1. Open the official bridge at bridge.cellframe.net\n"
            f"2. Connect your wallet (MetaMask/Trust Wallet)\n"
            f"3. Complete the transaction\n\n"
            f"We'll monitor your transaction and notify you of updates!\n\n"
            f"<i>Use /status to check progress anytime.</i>\n"
        )
        
        # Add CFSCAN link if destination is CF-20
        if dst == "cf":
            dst_addr = data.get("dst_address", "")
            if dst_addr:
                cfscan_link = cfscan.format_address_link(dst_addr, "View on CFSCAN")
                success_text += f"\n📊 Destination address: {cfscan_link}"
        
        await callback.message.edit_text(
            success_text,
            reply_markup=action_keyboard(session_id),
        )
        await callback.answer("✅ Session created!")

    # ==================== Binding Flow Handlers ====================

    @router.message(BindFlow.waiting_chain, F.text.regexp(r"^(ETH|BSC|CF20|eth|bsc|cf20):[a-zA-Z0-9_-]+$"))
    async def handle_bind_input(message: types.Message, state: FSMContext) -> None:
        """Handle address binding input."""
        parts = message.text.split(":", 1)
        chain = parts[0].upper()
        address = parts[1].strip()
        
        # Validate
        chain_map = {"ETH": "ethereum", "BSC": "bsc", "CF20": "cf20"}
        chain_type = chain_map.get(chain, "ethereum")
        
        if not validate_address(address, chain_type):
            await message.answer(
                f"❌ Invalid {chain} address format.\n"
                f"Please check and try again:"
            )
            return
        
        # Save binding
        binding_storage.bind(message.from_user.id, chain, address)
        await state.clear()
        
        await message.answer(
            f"✅ <b>Address Bound Successfully!</b>\n\n"
            f"Network: {chain}\n"
            f"Address: <code>{address[:10]}...{address[-8:]}</code>\n\n"
            f"You can now use this address in bridge sessions."
        )

    @router.message(BindFlow.waiting_chain)
    async def invalid_bind_format(message: types.Message) -> None:
        """Handle invalid binding format."""
        await message.answer(
            "❌ Invalid format.\n\n"
            "<b>Use:</b> <code>NETWORK:address</code>\n\n"
            "<b>Example:</b> <code>ETH:0x742d35Cc6...</code>"
        )

    # ==================== Callback Query Handlers ====================

    @router.callback_query(F.data.startswith("status:"))
    async def handle_status_button(callback: types.CallbackQuery) -> None:
        """Handle status check button."""
        session_id = callback.data.split(":", 1)[1]
        await callback.answer("Checking status...")
        await callback.message.answer(
            f"🔍 Checking status for session:\n"
            f"<code>{session_id}</code>\n\n"
            f"<i>Detailed status tracking coming soon!</i>"
        )

    # ==================== Fallback Handler ====================

    @router.message()
    async def fallback(message: types.Message, state: FSMContext) -> None:
        """Handle unrecognized messages."""
        current_state = await state.get_state()
        
        if current_state:
            await message.answer(
                "❌ Invalid input. Please follow the instructions or use /cancel to abort."
            )
        else:
            await message.answer(
                "I don't understand. Use /help to see available commands."
            )

    # Register router
    dp.include_router(router)


__all__ = ["register_handlers"]

