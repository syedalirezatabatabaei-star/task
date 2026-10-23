"""Tests for permission management."""
import pytest


def test_list_permissions(client, auth_headers_admin):
    resp = client.get("/api/v1/permissions", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) > 0
    codes = [p["code"] for p in data]
    assert "dashboard.view" in codes
    assert "tasks.submit" in codes
    assert "notifications.manage" in codes


def test_list_permissions_non_admin(client, auth_headers_user):
    resp = client.get("/api/v1/permissions", headers=auth_headers_user)
    assert resp.status_code == 403


def test_get_user_permissions(client, auth_headers_admin, regular_user):
    resp = client.get(f"/api/v1/users/{regular_user.id}/permissions", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "permissions" in data


def test_update_user_permissions(client, auth_headers_admin, regular_user):
    resp = client.put(
        f"/api/v1/users/{regular_user.id}/permissions",
        headers=auth_headers_admin,
        json={"permission_codes": ["dashboard.view", "tasks.view", "tasks.submit"]},
    )
    assert resp.status_code == 200

    # Verify permissions were set
    resp2 = client.get(f"/api/v1/users/{regular_user.id}/permissions", headers=auth_headers_admin)
    perms = resp2.json()["data"]["permissions"]
    assert "dashboard.view" in perms
    assert "tasks.submit" in perms


def test_update_user_permissions_invalid_code(client, auth_headers_admin, regular_user):
    resp = client.put(
        f"/api/v1/users/{regular_user.id}/permissions",
        headers=auth_headers_admin,
        json={"permission_codes": ["invalid.permission.code"]},
    )
    assert resp.status_code == 400


def test_permission_enforced_on_backend(client, regular_user, db):
    """User without projects.view cannot list projects."""
    from app.models.permission import UserPermission
    db.query(UserPermission).filter(UserPermission.user_id == regular_user.id).delete()
    db.commit()

    from app.core.security import create_access_token
    token = create_access_token({"sub": str(regular_user.id)})
    resp = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

def test_notification_permission_can_be_granted_and_revoked(client, auth_headers_admin, regular_user):
    grant = client.put(
        f"/api/v1/users/{regular_user.id}/permissions",
        headers=auth_headers_admin,
        json={"permission_codes": ["dashboard.view", "notifications.manage"]},
    )
    assert grant.status_code == 200

    listed = client.get(
        f"/api/v1/users/{regular_user.id}/permissions",
        headers=auth_headers_admin,
    )
    assert "notifications.manage" in listed.json()["data"]["permissions"]

    revoke = client.put(
        f"/api/v1/users/{regular_user.id}/permissions",
        headers=auth_headers_admin,
        json={"permission_codes": ["dashboard.view"]},
    )
    assert revoke.status_code == 200
    listed_after = client.get(
        f"/api/v1/users/{regular_user.id}/permissions",
        headers=auth_headers_admin,
    )
    assert "notifications.manage" not in listed_after.json()["data"]["permissions"]

