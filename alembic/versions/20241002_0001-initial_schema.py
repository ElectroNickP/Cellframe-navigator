"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-10-02 00:01:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('language_code', sa.String(length=8), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create wallet_bindings table
    op.create_table(
        'wallet_bindings',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('chain', sa.String(length=64), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create bridge_sessions table
    op.create_table(
        'bridge_sessions',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('direction', sa.String(length=64), nullable=False),
        sa.Column('token', sa.String(length=32), nullable=False),
        sa.Column('amount', sa.String(length=64), nullable=False),
        sa.Column('src_address', sa.String(length=255), nullable=True),
        sa.Column('dst_address', sa.String(length=255), nullable=True),
        sa.Column('src_network', sa.String(length=32), nullable=True),
        sa.Column('dst_network', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('estimated_fee', sa.String(length=64), nullable=True),
        sa.Column('estimated_time_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index(op.f('ix_bridge_sessions_session_id'), 'bridge_sessions', ['session_id'], unique=True)

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('chain', sa.String(length=32), nullable=False),
        sa.Column('hash', sa.String(length=128), nullable=False),
        sa.Column('block_number', sa.Integer(), nullable=True),
        sa.Column('confirmations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('confirmations_required', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('amount', sa.String(length=64), nullable=True),
        sa.Column('fee', sa.String(length=64), nullable=True),
        sa.Column('from_address', sa.String(length=255), nullable=True),
        sa.Column('to_address', sa.String(length=255), nullable=True),
        sa.Column('confirmed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['bridge_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_hash'), 'transactions', ['hash'], unique=False)

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['bridge_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('alerts')
    op.drop_index(op.f('ix_transactions_hash'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_bridge_sessions_session_id'), table_name='bridge_sessions')
    op.drop_table('bridge_sessions')
    op.drop_table('wallet_bindings')
    op.drop_table('users')



