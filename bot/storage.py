from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class BridgeSession:
    session_id: str
    user_id: int
    direction: str
    token: str
    amount: str
    status: str = "pending"


class BindingStorage:
    """In-memory storage for bindings and bridge sessions.

    The production implementation should use the shared database.
    """

    def __init__(self) -> None:
        self._bindings: Dict[int, Dict[str, str]] = {}
        self._sessions: Dict[int, List[BridgeSession]] = {}

    def bind(self, user_id: int, chain: str, address: str) -> None:
        self._bindings.setdefault(user_id, {})[chain.lower()] = address

    def get_binding(self, user_id: int, chain: str) -> str | None:
        return self._bindings.get(user_id, {}).get(chain.lower())

    def list_bindings(self, user_id: int) -> Dict[str, str]:
        return self._bindings.get(user_id, {})

    def create_session(self, user_id: int, direction: str, token: str, amount: str) -> BridgeSession:
        session = BridgeSession(
            session_id=uuid.uuid4().hex,
            user_id=user_id,
            direction=direction,
            token=token,
            amount=amount,
        )
        self._sessions.setdefault(user_id, []).append(session)
        return session

    def list_sessions(self, user_id: int) -> List[BridgeSession]:
        return self._sessions.get(user_id, [])

    def update_session_status(self, user_id: int, session_id: str, status: str) -> None:
        for session in self._sessions.get(user_id, []):
            if session.session_id == session_id:
                session.status = status
                return


__all__ = ["BindingStorage", "BridgeSession"]
