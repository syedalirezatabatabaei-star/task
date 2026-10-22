"""Tests for authentication endpoints."""
import pytest


def test_login_success(client, admin_user):
    resp = client.post("/api/v1/auth/login", json={"username": "testadmin", "password": "adminpass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testadmin"
    assert data["user"]["role"] == "ADMIN"


def test_login_wrong_password(client, admin_user):
    resp = client.post("/api/v1/auth/login", json={"username": "testadmin", "password": "wrongpass"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_nonexistent_user(client):
    resp = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "pass"})
    assert resp.status_code == 401


def test_login_inactive_user(client, db):
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    user = User(
        username="inactive",
        password_hash=hash_password("pass123"),
        role=UserRole.USER,
        is_active=False,
    )
    db.add(user)
    db.commit()

    resp = client.post("/api/v1/auth/login", json={"username": "inactive", "password": "pass123"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ACCOUNT_DISABLED"


def test_get_me_authenticated(client, auth_headers_admin):
    resp = client.get("/api/v1/auth/me", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == "testadmin"
    assert "permissions" in data


def test_get_me_unauthenticated(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_logout(client, auth_headers_admin):
    resp = client.post("/api/v1/auth/logout", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_invalid_token(client):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert resp.status_code == 401
