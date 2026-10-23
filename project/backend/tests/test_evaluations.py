"""Tests for evaluation endpoints."""
import pytest


@pytest.fixture
def submitted_task(client, auth_headers_admin, regular_user):
    proj = client.post("/api/v1/projects", headers=auth_headers_admin, json={
        "name": "ارزیابی پروژه", "status": "ACTIVE"
    }).json()["data"]

    membership = client.post(
        f"/api/v1/projects/{proj['id']}/members",
        headers=auth_headers_admin,
        json={"user_id": regular_user.id, "project_role": "عضو"},
    )
    assert membership.status_code == 200

    task = client.post("/api/v1/tasks", headers=auth_headers_admin, json={
        "title": "وظیفه ارزیابی",
        "project_id": proj["id"],
        "assigned_to": regular_user.id,
        "priority": "MEDIUM",
    }).json()["data"]

    client.patch(f"/api/v1/tasks/{task['id']}/status", headers=auth_headers_admin, json={"status": "IN_PROGRESS"})
    client.patch(f"/api/v1/tasks/{task['id']}/status", headers=auth_headers_admin, json={"status": "SUBMITTED"})
    return task


def test_create_evaluation(client, auth_headers_admin, submitted_task):
    resp = client.post(f"/api/v1/tasks/{submitted_task['id']}/evaluations", headers=auth_headers_admin, json={
        "score": 87.5,
        "comment": "عملکرد خوب",
        "strengths": "کد تمیز",
        "weaknesses": "خطاها بهتر handle شود",
    })
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["score"] == 87.5
    assert data["task_id"] == submitted_task["id"]


def test_score_out_of_range(client, auth_headers_admin, submitted_task):
    resp = client.post(f"/api/v1/tasks/{submitted_task['id']}/evaluations", headers=auth_headers_admin, json={
        "score": 150.0,
    })
    assert resp.status_code == 422


def test_score_negative(client, auth_headers_admin, submitted_task):
    resp = client.post(f"/api/v1/tasks/{submitted_task['id']}/evaluations", headers=auth_headers_admin, json={
        "score": -5.0,
    })
    assert resp.status_code == 422


def test_list_evaluations(client, auth_headers_admin, submitted_task):
    client.post(f"/api/v1/tasks/{submitted_task['id']}/evaluations", headers=auth_headers_admin, json={"score": 90})
    resp = client.get(f"/api/v1/tasks/{submitted_task['id']}/evaluations", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


def test_update_evaluation(client, auth_headers_admin, submitted_task):
    create_resp = client.post(f"/api/v1/tasks/{submitted_task['id']}/evaluations", headers=auth_headers_admin, json={
        "score": 70,
        "comment": "نیاز به بهبود",
    })
    eval_id = create_resp.json()["data"]["id"]

    resp = client.put(f"/api/v1/evaluations/{eval_id}", headers=auth_headers_admin, json={
        "score": 85,
        "comment": "بهتر شد",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["score"] == 85.0


def test_evaluate_non_submitted_task(client, auth_headers_admin, regular_user):
    proj = client.post("/api/v1/projects", headers=auth_headers_admin, json={
        "name": "p2", "status": "ACTIVE"
    }).json()["data"]

    membership = client.post(
        f"/api/v1/projects/{proj['id']}/members",
        headers=auth_headers_admin,
        json={"user_id": regular_user.id, "project_role": "عضو"},
    )
    assert membership.status_code == 200

    task = client.post("/api/v1/tasks", headers=auth_headers_admin, json={
        "title": "وظیفه TODO",
        "project_id": proj["id"],
        "assigned_to": regular_user.id,
        "priority": "LOW",
    }).json()["data"]

    resp = client.post(f"/api/v1/tasks/{task['id']}/evaluations", headers=auth_headers_admin, json={"score": 80})
    assert resp.status_code == 422
