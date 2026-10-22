"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-10-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def create_table_if_missing(table_name: str, *args, **kwargs):
    """Create a table only when it is absent from the current database."""
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(table_name):
        print(f"Alembic: table {table_name!r} already exists; skipping creation.", flush=True)
        return None
    return op.create_table(table_name, *args, **kwargs)


def create_index_if_missing(index_name: str, table_name: str, columns, **kwargs):
    """Create an index only when it is absent; supports safe startup retries."""
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        raise RuntimeError(f"Cannot create index {index_name!r}: table {table_name!r} does not exist.")
    existing = {index.get("name") for index in inspector.get_indexes(table_name)}
    if index_name in existing:
        print(f"Alembic: index {index_name!r} already exists; skipping creation.", flush=True)
        return None
    return op.create_index(index_name, table_name, columns, **kwargs)


def upgrade() -> None:
    # users
    create_table_if_missing("users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="USER"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW() ON UPDATE NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    create_index_if_missing("ix_users_username", "users", ["username"])

    # permissions
    create_table_if_missing("permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, sqlite_autoincrement=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    create_index_if_missing("ix_permissions_code", "permissions", ["code"])

    # user_permissions
    create_table_if_missing("user_permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "permission_id", name="uq_user_permission"),
    )

    # projects
    create_table_if_missing("projects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("show_roadmap", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW() ON UPDATE NOW()")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # project_members
    create_table_if_missing("project_members",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("project_role", sa.String(100), nullable=True),
        sa.Column("joined_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )

    # project_stages
    create_table_if_missing("project_stages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW() ON UPDATE NOW()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # tasks
    create_table_if_missing("tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("stage_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(20), nullable=False, server_default="TODO"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW() ON UPDATE NOW()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stage_id"], ["project_stages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # evaluations
    create_table_if_missing("evaluations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("evaluator_id", sa.BigInteger(), nullable=True),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("strengths", sa.Text(), nullable=True),
        sa.Column("weaknesses", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW() ON UPDATE NOW()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluator_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # attachments
    create_table_if_missing("attachments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # audit_logs
    create_table_if_missing("audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    create_index_if_missing("ix_audit_logs_action", "audit_logs", ["action"])
    create_index_if_missing("ix_audit_logs_user_id", "audit_logs", ["user_id"])

    # Seed permissions
    op.execute("""
        INSERT IGNORE INTO permissions (code, name, description) VALUES
        ('dashboard.view', 'مشاهده داشبورد', 'دسترسی به داشبورد اصلی'),
        ('users.view', 'مشاهده کاربران', 'مشاهده لیست کاربران'),
        ('users.create', 'ایجاد کاربر', 'ایجاد کاربر جدید'),
        ('users.edit', 'ویرایش کاربر', 'ویرایش اطلاعات کاربر'),
        ('users.delete', 'حذف کاربر', 'حذف کاربر'),
        ('projects.view', 'مشاهده پروژه‌ها', 'مشاهده لیست پروژه‌ها'),
        ('projects.create', 'ایجاد پروژه', 'ایجاد پروژه جدید'),
        ('projects.edit', 'ویرایش پروژه', 'ویرایش اطلاعات پروژه'),
        ('projects.delete', 'حذف پروژه', 'حذف پروژه'),
        ('projects.members.manage', 'مدیریت اعضای پروژه', 'افزودن و حذف اعضای پروژه'),
        ('stages.view', 'مشاهده مراحل', 'مشاهده مراحل پروژه'),
        ('stages.create', 'ایجاد مرحله', 'ایجاد مرحله جدید'),
        ('stages.edit', 'ویرایش مرحله', 'ویرایش مرحله'),
        ('stages.delete', 'حذف مرحله', 'حذف مرحله'),
        ('tasks.view', 'مشاهده وظایف', 'مشاهده وظایف'),
        ('tasks.create', 'ایجاد وظیفه', 'ایجاد وظیفه جدید'),
        ('tasks.edit', 'ویرایش وظیفه', 'ویرایش وظیفه'),
        ('tasks.delete', 'حذف وظیفه', 'حذف وظیفه'),
        ('tasks.assign', 'تخصیص وظیفه', 'تخصیص وظیفه به کاربر'),
        ('tasks.submit', 'ارسال وظیفه', 'ارسال وظیفه برای بررسی'),
        ('roadmap.view', 'مشاهده نقشه راه', 'مشاهده نقشه راه پروژه'),
        ('roadmap.manage', 'مدیریت نقشه راه', 'مدیریت نقشه راه پروژه'),
        ('evaluations.view', 'مشاهده ارزیابی', 'مشاهده ارزیابی‌ها'),
        ('evaluations.create', 'ایجاد ارزیابی', 'ایجاد ارزیابی جدید'),
        ('evaluations.edit', 'ویرایش ارزیابی', 'ویرایش ارزیابی'),
        ('reports.view', 'مشاهده گزارش‌ها', 'مشاهده گزارش‌ها'),
        ('attachments.view', 'مشاهده پیوست‌ها', 'مشاهده فایل‌های پیوست'),
        ('attachments.upload', 'آپلود پیوست', 'آپلود فایل پیوست'),
        ('audit_logs.view', 'مشاهده لاگ‌ها', 'مشاهده لاگ‌های سیستم')
    """)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("attachments")
    op.drop_table("evaluations")
    op.drop_table("tasks")
    op.drop_table("project_stages")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("user_permissions")
    op.drop_table("permissions")
    op.drop_table("users")
