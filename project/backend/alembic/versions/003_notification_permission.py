"""Seed notification management permission.

Revision ID: 003
Revises: 002
"""
from typing import Sequence, Union
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT IGNORE INTO permissions (code, name, description)
        VALUES ('notifications.manage', 'مدیریت اعلان‌ها', 'انتشار اعلان عمومی و خصوصی')
    """)


def downgrade() -> None:
    op.execute("DELETE FROM permissions WHERE code = 'notifications.manage'")
