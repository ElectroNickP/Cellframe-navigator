from __future__ import annotations

from typing import Iterable

from sqlalchemy import select

from data.database import get_session
from data.models import Alert, BridgeSession, Transaction, User, WalletBinding


async def get_or_create_user(user_id: int, username: str | None, language_code: str | None) -> User:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(id=user_id, username=username, language_code=language_code)
            session.add(user)
        else:
            user.username = username
            user.language_code = language_code
        await session.commit()
        await session.refresh(user)
        return user


async def list_wallet_bindings(user_id: int) -> Iterable[WalletBinding]:
    async with get_session() as session:
        result = await session.execute(
            select(WalletBinding).where(WalletBinding.user_id == user_id)
        )
        return result.scalars().all()


async def save_bridge_session(session_data: BridgeSession) -> BridgeSession:
    async with get_session() as session:
        session.merge(session_data)
        await session.commit()
        return session_data


async def add_transaction(transaction: Transaction) -> Transaction:
    async with get_session() as session:
        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)
        return transaction


async def create_alert(alert: Alert) -> Alert:
    async with get_session() as session:
        session.add(alert)
        await session.commit()
        await session.refresh(alert)
        return alert


async def mark_alert_sent(alert_id: int) -> None:
    async with get_session() as session:
        result = await session.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one()
        alert.sent = True
        await session.commit()
