"""Tests for project and stage endpoints."""
import pytest


@pytest.fixture
def project(client, auth_headers_admin, db):
    resp = client.post("/api/v1/projects", headers=auth_headers_admin, json={
        "name": "پروژه تست",
        "description": "توضیحات تست",
        "status": "ACTIVE",
        "show_roadmap": True,
    })
    assert resp.status_code == 201
    return resp.json()["data"]


def test_create_project(client, auth_headers_admin):
    resp = client.post("/api/v1/projects", headers=auth_headers_admin, json={
        "name": "پروژه جدید",
        "status": "PLANNED",
    })
    assert resp.status_code == 201
    assert resp.json()["data"]["name"] == "پروژه جدید"


def test_list_projects(client, auth_headers_admin, project):
    resp = client.get("/api/v1/projects", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_get_project(client, auth_headers_admin, project):
    resp = client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == project["id"]


def test_update_project(client, auth_headers_admin, project):
    resp = client.put(f"/api/v1/projects/{project['id']}", headers=auth_headers_admin, json={
        "name": "پروژه ویرایش‌شده",
        "status": "COMPLETED",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "پروژه ویرایش‌شده"


def test_delete_project(client, auth_headers_admin, project):
    resp = client.delete(f"/api/v1/projects/{project['id']}", headers=auth_headers_admin)
    assert resp.status_code == 200

    resp2 = client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers_admin)
    assert resp2.status_code == 404


def test_add_member(client, auth_headers_admin, project, regular_user):
    resp = client.post(f"/api/v1/projects/{project['id']}/members", headers=auth_headers_admin, json={
        "user_id": regular_user.id,
        "project_role": "توسعه‌دهنده",
    })
    assert resp.status_code == 200


def test_add_duplicate_member(client, auth_headers_admin, project, regular_user):
    client.post(f"/api/v1/projects/{project['id']}/members", headers=auth_headers_admin, json={
        "user_id": regular_user.id,
    })
    resp = client.post(f"/api/v1/projects/{project['id']}/members", headers=auth_headers_admin, json={
        "user_id": regular_user.id,
    })
    assert resp.status_code == 409


def test_create_stage(client, auth_headers_admin, project):
    resp = client.post(f"/api/v1/projects/{project['id']}/stages", headers=auth_headers_admin, json={
        "name": "مرحله اول",
        "order_index": 1,
    })
    assert resp.status_code == 201
    assert resp.json()["data"]["name"] == "مرحله اول"
