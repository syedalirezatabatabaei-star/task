"""
Central permission codes used throughout the application.
"""

DASHBOARD_VIEW = "dashboard.view"

USERS_VIEW = "users.view"
USERS_CREATE = "users.create"
USERS_EDIT = "users.edit"
USERS_DELETE = "users.delete"

PROJECTS_VIEW = "projects.view"
PROJECTS_CREATE = "projects.create"
PROJECTS_EDIT = "projects.edit"
PROJECTS_DELETE = "projects.delete"
PROJECTS_MEMBERS_MANAGE = "projects.members.manage"

STAGES_VIEW = "stages.view"
STAGES_CREATE = "stages.create"
STAGES_EDIT = "stages.edit"
STAGES_DELETE = "stages.delete"

TASKS_VIEW = "tasks.view"
TASKS_CREATE = "tasks.create"
TASKS_EDIT = "tasks.edit"
TASKS_DELETE = "tasks.delete"
TASKS_ASSIGN = "tasks.assign"
TASKS_SUBMIT = "tasks.submit"

ROADMAP_VIEW = "roadmap.view"
ROADMAP_MANAGE = "roadmap.manage"

EVALUATIONS_VIEW = "evaluations.view"
EVALUATIONS_CREATE = "evaluations.create"
EVALUATIONS_EDIT = "evaluations.edit"

REPORTS_VIEW = "reports.view"

ATTACHMENTS_VIEW = "attachments.view"
ATTACHMENTS_UPLOAD = "attachments.upload"

AUDIT_LOGS_VIEW = "audit_logs.view"

NOTIFICATIONS_MANAGE = "notifications.manage"

ALL_PERMISSIONS = [
    (DASHBOARD_VIEW, "مشاهده داشبورد", "دسترسی به داشبورد اصلی"),
    (USERS_VIEW, "مشاهده کاربران", "مشاهده لیست کاربران"),
    (USERS_CREATE, "ایجاد کاربر", "ایجاد کاربر جدید"),
    (USERS_EDIT, "ویرایش کاربر", "ویرایش اطلاعات کاربر"),
    (USERS_DELETE, "حذف کاربر", "حذف کاربر"),
    (PROJECTS_VIEW, "مشاهده پروژه‌ها", "مشاهده لیست پروژه‌ها"),
    (PROJECTS_CREATE, "ایجاد پروژه", "ایجاد پروژه جدید"),
    (PROJECTS_EDIT, "ویرایش پروژه", "ویرایش اطلاعات پروژه"),
    (PROJECTS_DELETE, "حذف پروژه", "حذف پروژه"),
    (PROJECTS_MEMBERS_MANAGE, "مدیریت اعضای پروژه", "افزودن و حذف اعضای پروژه"),
    (STAGES_VIEW, "مشاهده مراحل", "مشاهده مراحل پروژه"),
    (STAGES_CREATE, "ایجاد مرحله", "ایجاد مرحله جدید"),
    (STAGES_EDIT, "ویرایش مرحله", "ویرایش مرحله"),
    (STAGES_DELETE, "حذف مرحله", "حذف مرحله"),
    (TASKS_VIEW, "مشاهده وظایف", "مشاهده وظایف"),
    (TASKS_CREATE, "ایجاد وظیفه", "ایجاد وظیفه جدید"),
    (TASKS_EDIT, "ویرایش وظیفه", "ویرایش وظیفه"),
    (TASKS_DELETE, "حذف وظیفه", "حذف وظیفه"),
    (TASKS_ASSIGN, "تخصیص وظیفه", "تخصیص وظیفه به کاربر"),
    (TASKS_SUBMIT, "ارسال وظیفه", "ارسال وظیفه برای بررسی"),
    (ROADMAP_VIEW, "مشاهده نقشه راه", "مشاهده نقشه راه پروژه"),
    (ROADMAP_MANAGE, "مدیریت نقشه راه", "مدیریت نقشه راه پروژه"),
    (EVALUATIONS_VIEW, "مشاهده ارزیابی", "مشاهده ارزیابی‌ها"),
    (EVALUATIONS_CREATE, "ایجاد ارزیابی", "ایجاد ارزیابی جدید"),
    (EVALUATIONS_EDIT, "ویرایش ارزیابی", "ویرایش ارزیابی"),
    (REPORTS_VIEW, "مشاهده گزارش‌ها", "مشاهده گزارش‌ها"),
    (ATTACHMENTS_VIEW, "مشاهده پیوست‌ها", "مشاهده فایل‌های پیوست"),
    (ATTACHMENTS_UPLOAD, "آپلود پیوست", "آپلود فایل پیوست"),
    (AUDIT_LOGS_VIEW, "مشاهده لاگ‌ها", "مشاهده لاگ‌های سیستم"),
    (NOTIFICATIONS_MANAGE, "مدیریت اعلان‌ها", "انتشار اعلان عمومی و خصوصی"),
]
