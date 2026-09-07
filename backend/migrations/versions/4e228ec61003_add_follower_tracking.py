"""add follower tracking

Revision ID: 4e228ec61003
Revises: 41f99bd6b005
Create Date: 2026-07-08 01:41:11.607101

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e228ec61003'
down_revision: Union[str, Sequence[str], None] = '41f99bd6b005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass


