from __future__ import annotations

import logging
from typing import Optional

from aiogram import F
from aiogram import Router
from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards import direction_keyboard, token_keyboard
from bot.storage import BindingStorage


logger = logging.getLogger(__name__)


class BridgeFlow(StatesGroup):
    choosing_direction = State()
    choosing_token = State()
    waiting_amount = State()


binding_storage = BindingStorage()


def register_handlers(dp: Router) -> None:
    router = Router()

    @router.message(Command("start", "help"))
    async def cmd_help(message: types.Message) -> None:
        await message.answer(
            "<b>Cellframe Navigator</b>\n\n"
            "/bridge - start bridging funds\n"
            "/status - check bridge session status\n"
            "/fees - learn about bridging fees\n"
            "/bind - link your blockchain addresses\n"
            "/help - show this message again"
        )

    @router.message(Command("bind"))
    async def cmd_bind(message: types.Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Send me the chain and address in the format <code>CHAIN:address</code>.")

    @router.message(Command("bridge"))
    async def cmd_bridge(message: types.Message, state: FSMContext) -> None:
        await state.set_state(BridgeFlow.choosing_direction)
        await message.answer("Choose the bridge direction:", reply_markup=direction_keyboard())

    @router.message(Command("status"))
    async def cmd_status(message: types.Message) -> None:
        sessions = binding_storage.list_sessions(message.from_user.id)
        if not sessions:
            await message.answer("You do not have active bridge sessions.")
            return

        response = "\n".join(
            f"Session <b>{session.session_id}</b>: {session.status}" for session in sessions
        )
        await message.answer(response)

    @router.message(Command("fees"))
    async def cmd_fees(message: types.Message) -> None:
        await message.answer(
            "Bridge fees depend on the selected chain and token."
            " They are updated automatically by the watcher service."
        )

    @router.callback_query(BridgeFlow.choosing_direction)
    async def choose_direction(callback: types.CallbackQuery, state: FSMContext) -> None:
        await state.update_data(direction=callback.data)
        await state.set_state(BridgeFlow.choosing_token)
        await callback.message.edit_text(
            "Great! Now pick the token you want to bridge:",
            reply_markup=token_keyboard(callback.data),
        )

    @router.callback_query(BridgeFlow.choosing_token)
    async def choose_token(callback: types.CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        await state.update_data(token=callback.data)
        await state.set_state(BridgeFlow.waiting_amount)
        await callback.message.edit_text(
            "Send the amount you want to bridge as a number.", reply_markup=None
        )
        logger.debug("Direction: %s token: %s", data.get("direction"), callback.data)

    @router.message(BridgeFlow.waiting_amount, F.text.regexp(r"^[0-9]*\.?[0-9]+$"))
    async def set_amount(message: types.Message, state: FSMContext) -> None:
        data = await state.get_data()
        amount = message.text
        session = binding_storage.create_session(
            user_id=message.from_user.id,
            direction=data.get("direction"),
            token=data.get("token"),
            amount=amount,
        )
        await message.answer(
            "Bridge session created!\n"
            f"Session ID: <code>{session.session_id}</code>\n"
            "We will notify you once the transaction is confirmed."
        )
        await state.clear()

    @router.message()
    async def fallback(message: types.Message) -> None:
        await message.answer("I do not understand. Use /help to see available commands.")

    dp.include_router(router)


__all__ = ["register_handlers"]
