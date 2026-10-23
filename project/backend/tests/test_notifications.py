"""Regression tests for private/public notification announcements and permissions."""
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.core.security import hash_password


def test_user_without_notification_permission_cannot_publish_or_list_recipients(
    client, auth_headers_user
):
    recipients = client.get(
        "/api/v1/notifications/recipients", headers=auth_headers_user
    )
    assert recipients.status_code == 403

    publish = client.post(
        "/api/v1/notifications/announcements",
        headers=auth_headers_user,
        json={
            "title": "محرمانه",
            "message": "نباید منتشر شود",
            "scope": "private",
            "recipient_user_id": 1,
        },
    )
    assert publish.status_code == 403


def test_private_announcement_is_visible_only_to_selected_recipient(
    client, auth_headers_admin, regular_user, db
):
    other = User(
        username="other-notification-user",
        password_hash=hash_password("otherpass123"),
        first_name="کاربر",
        last_name="دیگر",
        role=UserRole.USER,
        is_active=True,
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    response = client.post(
        "/api/v1/notifications/announcements",
        headers=auth_headers_admin,
        json={
            "title": "اعلان خصوصی",
            "message": "فقط برای گیرنده",
            "scope": "private",
            "recipient_user_id": regular_user.id,
        },
    )
    assert response.status_code == 201
    assert response.json()["data"]["recipient_count"] == 1

    rows = db.query(Notification).filter(Notification.title == "اعلان خصوصی").all()
    assert len(rows) == 1
    assert rows[0].user_id == regular_user.id
    assert rows[0].scope == "private"
    assert rows[0].is_read is False
    assert db.query(Notification).filter(Notification.user_id == other.id).count() == 0

    from app.core.security import create_access_token
    other_headers = {"Authorization": f"Bearer {create_access_token({'sub': str(other.id)})}"}
    forbidden_read = client.patch(
        f"/api/v1/notifications/{rows[0].id}/read", headers=other_headers
    )
    assert forbidden_read.status_code == 404


def test_public_announcement_fans_out_to_active_users(client, auth_headers_admin, regular_user, db):
    response = client.post(
        "/api/v1/notifications/announcements",
        headers=auth_headers_admin,
        json={
            "title": "اعلان عمومی",
            "message": "برای همه کاربران فعال",
            "scope": "public",
        },
    )
    assert response.status_code == 201

    active_count = db.query(User).filter(User.is_active.is_(True)).count()
    rows = db.query(Notification).filter(Notification.title == "اعلان عمومی").all()
    assert response.json()["data"]["recipient_count"] == active_count
    assert len(rows) == active_count
    assert all(row.scope == "public" and row.is_read is False for row in rows)
    assert {row.user_id for row in rows} == {
        user.id for user in db.query(User).filter(User.is_active.is_(True)).all()
    }


def test_private_announcement_requires_a_valid_active_recipient(client, auth_headers_admin):
    missing_recipient = client.post(
        "/api/v1/notifications/announcements",
        headers=auth_headers_admin,
        json={"title": "اعلان", "message": "متن", "scope": "private"},
    )
    assert missing_recipient.status_code == 422

    unknown_recipient = client.post(
        "/api/v1/notifications/announcements",
        headers=auth_headers_admin,
        json={
            "title": "اعلان",
            "message": "متن",
            "scope": "private",
            "recipient_user_id": 99999999,
        },
    )
    assert unknown_recipient.status_code == 404
