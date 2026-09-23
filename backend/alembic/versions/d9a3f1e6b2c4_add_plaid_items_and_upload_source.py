"""add plaid_items and upload.source

Revision ID: d9a3f1e6b2c4
Revises: c5d8e2a1b7f3
Create Date: 2026-09-22 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd9a3f1e6b2c4'
down_revision: str | Sequence[str] | None = 'c5d8e2a1b7f3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'plaid_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.String(), nullable=False),
        sa.Column('access_token', sa.String(), nullable=False),
        sa.Column('institution_name', sa.String(), nullable=True),
        sa.Column('cursor', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_plaid_items_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('plaid_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_plaid_items_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_plaid_items_item_id'), ['item_id'], unique=True)

    with op.batch_alter_table('uploads', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source', sa.String(), server_default='csv', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('uploads', schema=None) as batch_op:
        batch_op.drop_column('source')

    with op.batch_alter_table('plaid_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_plaid_items_item_id'))
        batch_op.drop_index(batch_op.f('ix_plaid_items_user_id'))
    op.drop_table('plaid_items')
