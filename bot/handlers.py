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
from bot.storage import BindingStorage
from watcher.validators import validate_address


logger = logging.getLogger(__name__)


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
            "/status [tx_hash] - Check transaction status\n"
            "/fees - View current bridge fees\n"
            "/bind - Link your blockchain addresses\n"
            "/mysessions - View your bridge sessions\n"
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
        """Check transaction status."""
        # Parse tx hash if provided
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            tx_hash = parts[1].strip()
            await message.answer(
                f"🔍 Checking status for transaction:\n"
                f"<code>{tx_hash}</code>\n\n"
                f"<i>Feature coming soon: Smart transaction diagnostics</i>"
            )
        else:
            # Show user's sessions
            sessions = binding_storage.list_sessions(message.from_user.id)
            if not sessions:
                await message.answer(
                    "You don't have any bridge sessions yet.\n"
                    "Use /bridge to create one!"
                )
                return

            response = "📊 <b>Your Bridge Sessions:</b>\n\n"
            for session in sessions[-5:]:  # Show last 5
                status_emoji = {
                    "pending": "⏳",
                    "processing": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                }.get(session.status, "❓")
                
                response += (
                    f"{status_emoji} <code>{session.session_id[:16]}...</code>\n"
                    f"   {session.direction.replace('_', ' → ').upper()} • "
                    f"{session.token} {session.amount}\n"
                    f"   Status: {session.status}\n\n"
                )
            
            await message.answer(response)

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
        sessions = binding_storage.list_sessions(message.from_user.id)
        
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
            
            response += (
                f"{idx}. {status_emoji} <b>{session.token}</b> {session.amount}\n"
                f"   Direction: {session.direction.replace('_to_', ' → ')}\n"
                f"   Status: {session.status}\n"
                f"   ID: <code>{session.session_id}</code>\n\n"
            )
        
        await message.answer(response)

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
        
        # Create session
        data = await state.get_data()
        session = binding_storage.create_session(
            user_id=callback.from_user.id,
            direction=data.get("direction"),
            token=data.get("token"),
            amount=data.get("amount"),
        )
        
        await state.clear()
        
        success_text = (
            "✅ <b>Bridge Session Created!</b>\n\n"
            f"Session ID: <code>{session.session_id}</code>\n\n"
            f"<b>Next Steps:</b>\n"
            f"1. Open the official bridge at bridge.cellframe.net\n"
            f"2. Connect your wallet (MetaMask/Trust Wallet)\n"
            f"3. Complete the transaction\n\n"
            f"We'll monitor your transaction and notify you of updates!\n\n"
            f"<i>Use /status to check progress anytime.</i>"
        )
        
        await callback.message.edit_text(
            success_text,
            reply_markup=action_keyboard(session.session_id),
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

