"""
Pytest configuration and fixtures.
Uses an in-memory SQLite database for isolation.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, MetaData, Table, Column, BigInteger, String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.core.permissions import ALL_PERMISSIONS
from app.models.user import User, UserRole
from app.models.permission import Permission, UserPermission
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _recreate_permissions_table() -> None:
    """Recreate the permissions table with SQLite AUTOINCREMENT.

    Tests use an in-memory SQLite database. Unlike the real MySQL schema
    (alembic/versions/001_initial_schema.py) and the declarative model, the
    table created by Base.metadata.create_all() has no AUTOINCREMENT, so the
    seeded permission rows could not get an auto-assigned id and the seed
    raised "NOT NULL constraint failed: permissions.id". Sledgehammer the
    table definition straight after create_all so the seed proceeds as
    intended.
    """
    from sqlalchemy import text as sql_text

    with engine.connect() as conn:
        conn.exec_driver_sql(
            "DROP TABLE IF EXISTS permissions;"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR(100) NOT NULL,
                name VARCHAR(150) NOT NULL,
                description TEXT,
                UNIQUE(code)
            );
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_permissions_code ON permissions(code);")  # type: ignore[arg-type]
        conn.commit()


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    _recreate_permissions_table()

    session = TestingSessionLocal()

    # Seed permissions
    for code, name, desc in ALL_PERMISSIONS:
        perm = Permission(code=code, name=name, description=desc)
        session.add(perm)
    session.commit()

    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    user = User(
        username="testadmin",
        password_hash=hash_password("adminpass123"),
        first_name="مدیر",
        last_name="تست",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def regular_user(db):
    user = User(
        username="testuser",
        password_hash=hash_password("userpass123"),
        first_name="کاربر",
        last_name="تست",
        role=UserRole.USER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(client, admin_user):
    resp = client.post("/api/v1/auth/login", json={"username": "testadmin", "password": "adminpass123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def user_token(client, regular_user, db):
    # Give user basic permissions
    from app.core import permissions as P
    perm_codes = [P.DASHBOARD_VIEW, P.PROJECTS_VIEW, P.TASKS_VIEW, P.TASKS_SUBMIT]
    for code in perm_codes:
        perm = db.query(Permission).filter(Permission.code == code).first()
        if perm:
            up = UserPermission(user_id=regular_user.id, permission_id=perm.id)
            db.add(up)
    db.commit()

    resp = client.post("/api/v1/auth/login", json={"username": "testuser", "password": "userpass123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers_admin(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def auth_headers_user(user_token):
    return {"Authorization": f"Bearer {user_token}"}
