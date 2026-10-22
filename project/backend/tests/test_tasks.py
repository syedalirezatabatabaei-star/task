"""Tests for task endpoints."""
import pytest


@pytest.fixture
def project_id(client, auth_headers_admin):
    resp = client.post("/api/v1/projects", headers=auth_headers_admin, json={
        "name": "پروژه وظایف",
        "status": "ACTIVE",
    })
    return resp.json()["data"]["id"]


@pytest.fixture
def task(client, auth_headers_admin, project_id, regular_user):
    resp = client.post("/api/v1/tasks", headers=auth_headers_admin, json={
        "title": "وظیفه تست",
        "description": "توضیحات",
        "project_id": project_id,
        "assigned_to": regular_user.id,
        "priority": "HIGH",
    })
    assert resp.status_code == 201
    return resp.json()["data"]


def test_create_task(client, auth_headers_admin, project_id, regular_user):
    resp = client.post("/api/v1/tasks", headers=auth_headers_admin, json={
        "title": "وظیفه جدید",
        "project_id": project_id,
        "assigned_to": regular_user.id,
        "priority": "MEDIUM",
    })
    assert resp.status_code == 201
    assert resp.json()["data"]["title"] == "وظیفه جدید"
    assert resp.json()["data"]["status"] == "TODO"


def test_list_tasks_admin(client, auth_headers_admin, task):
    resp = client.get("/api/v1/tasks", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


def test_list_tasks_user_sees_only_own(client, auth_headers_user, task, regular_user):
    """Regular user only sees tasks assigned to them."""
    resp = client.get("/api/v1/tasks", headers=auth_headers_user)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    for item in items:
        assert item["assigned_to"] == regular_user.id


def test_task_status_transition_valid(client, auth_headers_admin, task):
    resp = client.patch(f"/api/v1/tasks/{task['id']}/status", headers=auth_headers_admin, json={
        "status": "IN_PROGRESS",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "IN_PROGRESS"


def test_task_status_transition_invalid(client, auth_headers_admin, task):
    """Cannot go from TODO directly to DONE."""
    resp = client.patch(f"/api/v1/tasks/{task['id']}/status", headers=auth_headers_admin, json={
        "status": "DONE",
    })
    assert resp.status_code == 422


def test_task_submit(client, auth_headers_user, task, regular_user, auth_headers_admin):
    """Move to IN_PROGRESS first, then user submits."""
    client.patch(f"/api/v1/tasks/{task['id']}/status", headers=auth_headers_admin, json={"status": "IN_PROGRESS"})
    resp = client.post(f"/api/v1/tasks/{task['id']}/submit", headers=auth_headers_user, json={
        "comment": "آماده بررسی",
        "progress": 100,
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "SUBMITTED"


def test_cross_user_task_access(client, db):
    """User cannot access another user's task."""
    from app.models.user import User, UserRole
    from app.models.task import Task
    from app.models.project import Project
    from app.core.security import hash_password, create_access_token
    from app.models.permission import Permission, UserPermission
    from app.core import permissions as P

    user2 = User(username="user2", password_hash=hash_password("pass"), role=UserRole.USER, is_active=True)
    db.add(user2)
    db.commit()

    perm = db.query(Permission).filter(Permission.code == P.TASKS_VIEW).first()
    edit_perm = db.query(Permission).filter(Permission.code == P.TASKS_EDIT).first()
    if perm:
        db.add(UserPermission(user_id=user2.id, permission_id=perm.id))
        db.commit()

    proj = Project(name="p", created_by=user2.id, status="ACTIVE")
    db.add(proj)
    db.commit()

    task = Task(title="private task", project_id=proj.id, assigned_to=user2.id, status="TODO", priority="MEDIUM")
    db.add(task)
    db.commit()

    # user2 token
    token = create_access_token({"sub": str(user2.id)})

    # Try accessing task with different user's token (but task belongs to user2, so this should work)
    resp = client.get(f"/api/v1/tasks/{task.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    # Create user3 who should NOT see user2's task
    user3 = User(username="user3", password_hash=hash_password("pass"), role=UserRole.USER, is_active=True)
    db.add(user3)
    db.commit()
    if perm:
        db.add(UserPermission(user_id=user3.id, permission_id=perm.id))
    if edit_perm:
        db.add(UserPermission(user_id=user3.id, permission_id=edit_perm.id))
    db.commit()

    token3 = create_access_token({"sub": str(user3.id)})
    headers3 = {"Authorization": f"Bearer {token3}"}
    resp3 = client.get(f"/api/v1/tasks/{task.id}", headers=headers3)
    assert resp3.status_code == 403
    edit_resp = client.put(f"/api/v1/tasks/{task.id}", headers=headers3, json={"title": "unauthorized update"})
    assert edit_resp.status_code == 403
    status_resp = client.patch(f"/api/v1/tasks/{task.id}/status", headers=headers3, json={"status": "IN_PROGRESS"})
    assert status_resp.status_code == 403
    progress_resp = client.patch(f"/api/v1/tasks/{task.id}/progress", headers=headers3, json={"progress": 50})
    assert progress_resp.status_code == 403


def test_submit_rejects_progress_out_of_range(client, auth_headers_admin, task):
    resp = client.post(f"/api/v1/tasks/{task['id']}/submit", headers=auth_headers_admin, json={"progress": 101})
    assert resp.status_code == 422
