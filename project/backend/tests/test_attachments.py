"""Attachment authorization regression tests."""
from app.core import permissions as P
from app.core.security import create_access_token
from app.models.attachment import Attachment
from app.models.permission import Permission, UserPermission
from app.models.project import Project, ProjectMember, ProjectStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User, UserRole


def test_nonmember_cannot_list_or_download_task_attachments(client, db, admin_user, regular_user):
    # A second user has the relevant API permission but is neither assigned to
    # the task nor a member of its project. Object-level authorization must win.
    outsider = User(
        username="attachment-outsider",
        password_hash="not-used-in-this-test",
        first_name="کاربر",
        last_name="غیرعضو",
        role=UserRole.USER,
        is_active=True,
    )
    db.add(outsider)
    db.flush()

    permission = db.query(Permission).filter(Permission.code == P.ATTACHMENTS_VIEW).first()
    assert permission is not None
    db.add(UserPermission(user_id=outsider.id, permission_id=permission.id))

    project = Project(
        name="پروژه پیوست خصوصی",
        status=ProjectStatus.ACTIVE,
        created_by=admin_user.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=regular_user.id, project_role="عضو"))

    task = Task(
        project_id=project.id,
        title="وظیفه خصوصی",
        assigned_to=regular_user.id,
        created_by=admin_user.id,
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.TODO,
    )
    db.add(task)
    db.flush()
    attachment = Attachment(
        task_id=task.id,
        uploaded_by=regular_user.id,
        original_filename="private.pdf",
        stored_filename="random.pdf",
        file_path="/not-created/private.pdf",
        mime_type="application/pdf",
        file_size=12,
    )
    db.add(attachment)
    db.commit()

    token = create_access_token({"sub": str(outsider.id)})
    headers = {"Authorization": f"Bearer {token}"}

    listed = client.get(f"/api/v1/tasks/{task.id}/attachments", headers=headers)
    assert listed.status_code == 403

    downloaded = client.get(f"/api/v1/attachments/{attachment.id}/download", headers=headers)
    assert downloaded.status_code == 403
