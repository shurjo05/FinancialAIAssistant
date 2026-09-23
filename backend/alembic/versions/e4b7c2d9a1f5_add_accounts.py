"""add accounts (balances)

Revision ID: e4b7c2d9a1f5
Revises: d9a3f1e6b2c4
Create Date: 2026-09-23 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e4b7c2d9a1f5'
down_revision: str | Sequence[str] | None = 'd9a3f1e6b2c4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('institution_name', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('mask', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('subtype', sa.String(), nullable=True),
        sa.Column('current_balance', sa.Float(), nullable=True),
        sa.Column('available_balance', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(), server_default='USD', nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_accounts_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_accounts_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_accounts_user_id'))
    op.drop_table('accounts')
