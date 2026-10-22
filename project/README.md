# سیستم مدیریت کارآموزی و پروژه

یک سیستم کامل مدیریت کارآموزی با FastAPI (Backend) و Vanilla JS/HTML (Frontend).

---

## معماری

```
Browser
   │
   ├── Frontend (Nginx) — Port 80
   │
   └── Backend (FastAPI/Uvicorn) — Port 8000
                │
                └── MySQL 8 — Port 3306 (internal)
```

## پیش‌نیازها

- Docker و Docker Compose
- یا Python 3.12+ و MySQL 8+ (بدون Docker)

---

## راه‌اندازی سریع با Docker

### ۱. کپی فایل محیطی
```bash
cp .env.example .env
```

### ۲. ویرایش `.env`
حتماً مقادیر زیر را تغییر دهید:
```env
SECRET_KEY=یک-رشته-تصادفی-طولانی
JWT_SECRET_KEY=یک-رشته-تصادفی-دیگر
MYSQL_PASSWORD=رمز-عبور-دیتابیس
ADMIN_PASSWORD=رمز-عبور-مدیر
ADMIN_USERNAME=admin
```

### ۳. ساخت و اجرا
```bash
docker compose up -d --build
```

### ۴. اجرای migrations
```bash
docker compose exec backend alembic upgrade head
```

### ۵. ایجاد اولین مدیر
```bash
docker compose exec backend python -m app.utils.create_admin
```

### ۶. دسترسی به سیستم
| آدرس | توضیح |
|------|-------|
| http://localhost | رابط کاربری |
| http://localhost:8000/docs | مستندات Swagger |
| http://localhost:8000/redoc | مستندات ReDoc |

---

## راه‌اندازی دستی (بدون Docker)

### Backend

```bash
cd backend

# ایجاد محیط مجازی
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# نصب وابستگی‌ها
pip install -r requirements.txt

# ایجاد فایل .env در پوشه backend
cp ../.env.example .env
# مقادیر را ویرایش کنید (MYSQL_HOST=localhost)

# اجرای migrations
alembic upgrade head

# ایجاد مدیر اول
python -m app.utils.create_admin

# اجرای سرور
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
# با هر web server ساده:
python -m http.server 3000
# یا npx serve . -p 3000
```

---

## متغیرهای محیطی

| متغیر | توضیح | پیش‌فرض |
|-------|-------|---------|
| `APP_NAME` | نام برنامه | Internship Management System |
| `SECRET_KEY` | کلید رمزنگاری | **الزامی** |
| `JWT_SECRET_KEY` | کلید JWT | **الزامی** |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | مدت اعتبار توکن (دقیقه) | 480 |
| `MYSQL_HOST` | هاست MySQL | mysql |
| `MYSQL_PORT` | پورت MySQL | 3306 |
| `MYSQL_DATABASE` | نام دیتابیس | internship_db |
| `MYSQL_USER` | کاربر MySQL | internship_user |
| `MYSQL_PASSWORD` | رمز MySQL | **الزامی** |
| `CORS_ORIGINS` | Origins مجاز | http://localhost |
| `UPLOAD_DIR` | پوشه آپلود | uploads |
| `MAX_UPLOAD_SIZE` | حداکثر حجم فایل (bytes) | 10485760 |
| `ADMIN_USERNAME` | نام کاربری مدیر اول | admin |
| `ADMIN_PASSWORD` | رمز مدیر اول | **الزامی** |

---

## Migrations

```bash
# مشاهده وضعیت
alembic current

# اعمال همه migrations
alembic upgrade head

# برگشت یک مرحله
alembic downgrade -1

# ایجاد migration جدید
alembic revision --autogenerate -m "توضیحات"
```

---

## تست‌ها

```bash
cd backend
pytest tests/ -v

# با پوشش کد
pytest tests/ --cov=app --cov-report=html
```

---

## ساختار پروژه

```
project/
├── backend/
│   ├── app/
│   │   ├── main.py           # نقطه ورود FastAPI
│   │   ├── core/             # پیکربندی، دیتابیس، امنیت
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── api/              # Route handlers
│   │   ├── services/         # Business logic
│   │   └── utils/            # ابزارها (create_admin)
│   ├── alembic/              # Database migrations
│   ├── tests/                # pytest tests
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   ├── users.html
│   ├── user-permissions.html
│   ├── projects.html
│   ├── project-details.html
│   ├── tasks.html
│   ├── task-details.html
│   ├── reports.html
│   └── assets/
│       ├── css/main.css
│       └── js/
│           ├── api.js        # API client مرکزی
│           ├── auth.js       # مدیریت احراز هویت
│           └── ui.js         # کامپوننت‌های UI
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## API Documentation

بعد از اجرای backend:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### نمونه endpoints

```
POST /api/v1/auth/login       ورود
GET  /api/v1/auth/me          اطلاعات کاربر جاری

GET  /api/v1/users            لیست کاربران
POST /api/v1/users            ایجاد کاربر

GET  /api/v1/projects         لیست پروژه‌ها
POST /api/v1/projects         ایجاد پروژه

GET  /api/v1/tasks            لیست وظایف
POST /api/v1/tasks/{id}/submit ارسال وظیفه

GET  /api/v1/dashboard/admin  داشبورد مدیر
GET  /api/v1/dashboard/user   داشبورد کاربر
```

---

## امنیت

- رمزهای عبور با **bcrypt** هش می‌شوند
- احراز هویت با **JWT** 
- بررسی دسترسی‌ها **server-side** انجام می‌شود
- SQL injection از طریق SQLAlchemy ORM جلوگیری می‌شود
- آپلود فایل با بررسی MIME type و حجم ایمن است
- هیچ اطلاعات حساسی در کد منبع ذخیره نمی‌شود

---

## License

MIT