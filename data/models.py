from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    language_code: Mapped[Optional[str]] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    wallet_bindings: Mapped[list["WalletBinding"]] = relationship(back_populates="user")
    bridge_sessions: Mapped[list["BridgeSession"]] = relationship(back_populates="user")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="user")


class WalletBinding(Base):
    __tablename__ = "wallet_bindings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    chain: Mapped[str] = mapped_column(String(64))
    address: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="wallet_bindings")


class BridgeSession(Base):
    __tablename__ = "bridge_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    direction: Mapped[str] = mapped_column(String(64))
    token: Mapped[str] = mapped_column(String(32))
    amount: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped[Optional[User]] = relationship(back_populates="bridge_sessions")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="session")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("bridge_sessions.id", ondelete="CASCADE"))
    chain: Mapped[str] = mapped_column(String(32))
    hash: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    amount: Mapped[Optional[str]] = mapped_column(String(64))
    fee: Mapped[Optional[str]] = mapped_column(String(64))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    session: Mapped[BridgeSession] = relationship(back_populates="transactions")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bridge_sessions.id", ondelete="SET NULL"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="alerts")
    session: Mapped[Optional[BridgeSession]] = relationship()


__all__ = [
    "Base",
    "User",
    "WalletBinding",
    "BridgeSession",
    "Transaction",
    "Alert",
]
