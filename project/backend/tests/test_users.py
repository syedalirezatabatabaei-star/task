"""Tests for user management endpoints."""
import pytest


def test_list_users_admin(client, auth_headers_admin, admin_user):
    resp = client.get("/api/v1/users", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert data["total"] >= 1


def test_list_users_no_permission(client, auth_headers_user, regular_user):
    resp = client.get("/api/v1/users", headers=auth_headers_user)
    assert resp.status_code == 403


def test_create_user_admin(client, auth_headers_admin):
    resp = client.post("/api/v1/users", headers=auth_headers_admin, json={
        "username": "newuser",
        "password": "newpass123",
        "first_name": "علی",
        "last_name": "رضایی",
        "role": "USER",
    })
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["username"] == "newuser"


def test_create_user_duplicate_username(client, auth_headers_admin, admin_user):
    resp = client.post("/api/v1/users", headers=auth_headers_admin, json={
        "username": "testadmin",
        "password": "pass123",
        "role": "USER",
    })
    assert resp.status_code == 409


def test_get_user(client, auth_headers_admin, admin_user):
    resp = client.get(f"/api/v1/users/{admin_user.id}", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == admin_user.id


def test_get_user_not_found(client, auth_headers_admin):
    resp = client.get("/api/v1/users/99999", headers=auth_headers_admin)
    assert resp.status_code == 404


def test_update_user(client, auth_headers_admin, regular_user):
    resp = client.put(f"/api/v1/users/{regular_user.id}", headers=auth_headers_admin, json={
        "first_name": "محمد",
        "last_name": "احمدی",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["first_name"] == "محمد"


def test_update_user_status(client, auth_headers_admin, regular_user):
    resp = client.patch(f"/api/v1/users/{regular_user.id}/status", headers=auth_headers_admin, json={
        "is_active": False,
    })
    assert resp.status_code == 200


def test_reset_password(client, auth_headers_admin, regular_user):
    resp = client.post(f"/api/v1/users/{regular_user.id}/reset-password", headers=auth_headers_admin, json={
        "new_password": "newpass456",
    })
    assert resp.status_code == 200
