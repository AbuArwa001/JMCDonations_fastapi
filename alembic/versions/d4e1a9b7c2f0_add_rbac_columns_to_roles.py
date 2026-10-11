"""Add RBAC columns to roles

Revision ID: d4e1a9b7c2f0
Revises: b2faddcc9420
Create Date: 2026-10-11 21:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e1a9b7c2f0'
down_revision: Union[str, Sequence[str], None] = 'b2faddcc9420'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema (additive only — no data is removed)."""
    op.add_column('roles', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('roles', sa.Column('permissions', sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column('roles', sa.Column('color', sa.String(length=20), nullable=True))
    op.add_column('roles', sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('roles', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('roles', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('roles', 'updated_at')
    op.drop_column('roles', 'created_at')
    op.drop_column('roles', 'is_system')
    op.drop_column('roles', 'color')
    op.drop_column('roles', 'permissions')
    op.drop_column('roles', 'description')
