from __future__ import annotations

import uuid
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


# ==================== Repository Classes ====================


class UserRepository:
    """Repository for User operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create(self, telegram_id: int, username: Optional[str] = None) -> User:
        """Get existing user or create new one."""
        result = await self.session.execute(
            select(User).where(User.id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            user = User(id=telegram_id, username=username)
            self.session.add(user)
            await self.session.flush()
        elif username and user.username != username:
            user.username = username
            await self.session.flush()
        
        return user
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by internal ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


class BridgeSessionRepository:
    """Repository for BridgeSession operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: int,
        direction: str,
        token: str,
        amount: str,
        src_address: str = "",
        dst_address: str = "",
        src_network: str = "",
        dst_network: str = "",
        estimated_fee: Optional[str] = None,
        estimated_time_seconds: Optional[int] = None,
    ) -> BridgeSession:
        """Create new bridge session."""
        session = BridgeSession(
            session_id=uuid.uuid4().hex,
            user_id=user_id,
            direction=direction,
            token=token,
            amount=amount,
            src_address=src_address,
            dst_address=dst_address,
            src_network=src_network,
            dst_network=dst_network,
            status="pending",
            estimated_fee=estimated_fee,
            estimated_time_seconds=estimated_time_seconds,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(session)
        await self.session.flush()
        return session
    
    async def get_by_session_id(self, session_id: str) -> Optional[BridgeSession]:
        """Get bridge session by session ID."""
        result = await self.session.execute(
            select(BridgeSession).where(BridgeSession.session_id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_user(self, user_id: int, limit: int = 10) -> list[BridgeSession]:
        """List bridge sessions for user."""
        result = await self.session.execute(
            select(BridgeSession)
            .where(BridgeSession.user_id == user_id)
            .order_by(BridgeSession.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def update_status(self, session_id: str, status: str) -> None:
        """Update session status."""
        result = await self.session.execute(
            select(BridgeSession).where(BridgeSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.status = status
            session.updated_at = datetime.utcnow()
            await self.session.flush()


class TransactionRepository:
    """Repository for Transaction operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        session_id: int,
        chain: str,
        tx_hash: str,
        confirmations_required: int = 12,
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
    ) -> Transaction:
        """Create new transaction record."""
        transaction = Transaction(
            session_id=session_id,
            chain=chain,
            hash=tx_hash,
            confirmations=0,
            confirmations_required=confirmations_required,
            status="pending",
            from_address=from_address,
            to_address=to_address,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction
    
    async def get_by_hash(self, tx_hash: str) -> Optional[Transaction]:
        """Get transaction by hash."""
        result = await self.session.execute(
            select(Transaction).where(Transaction.hash == tx_hash)
        )
        return result.scalar_one_or_none()
    
    async def update_status(
        self,
        tx_hash: str,
        confirmations: int,
        block_number: Optional[int] = None,
        status: Optional[str] = None,
    ) -> None:
        """Update transaction confirmations and status."""
        result = await self.session.execute(
            select(Transaction).where(Transaction.hash == tx_hash)
        )
        tx = result.scalar_one_or_none()
        if tx:
            tx.confirmations = confirmations
            if block_number:
                tx.block_number = block_number
            if status:
                tx.status = status
            if confirmations >= tx.confirmations_required:
                tx.confirmed = True
                tx.status = "confirmed"
            tx.updated_at = datetime.utcnow()
            await self.session.flush()
    
    async def list_pending(self, limit: int = 100) -> list[Transaction]:
        """List pending transactions for monitoring."""
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.confirmed == False)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


__all__ = [
    "get_or_create_user",
    "list_wallet_bindings",
    "save_bridge_session",
    "add_transaction",
    "create_alert",
    "mark_alert_sent",
    "UserRepository",
    "BridgeSessionRepository",
    "TransactionRepository",
]
