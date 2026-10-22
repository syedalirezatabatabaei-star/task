# سیستم مدیریت تسک

سامانه مدیریت پروژه و تسک با FastAPI، HTML/CSS/JavaScript و MySQL 8.

## معماری استقرار

- دامنه سامانه: `task.tinateck.ir`
- پورت داخلی فرانت‌اند روی سرور: `127.0.0.1:1597`
- Nginx میزبان درخواست‌ها را به پورت 1597 می‌فرستد.
- Nginx داخل کانتینر مسیرهای `/api/` و `/uploads/` را به Backend هدایت می‌کند.
- Backend و MySQL به اینترنت پورت منتشر نمی‌کنند.
- دامنه اصلی `tinateck.ir` در کانفیگ این پروژه تعریف نشده و برای وب‌سایت جداگانه شما آزاد می‌ماند.

## آیا دیتابیس INSERT دارد؟

بله. migration موجود در `backend/alembic/versions/001_initial_schema.py` ساختار جدول‌ها را می‌سازد و مجوزهای اولیه را با `INSERT INTO permissions` وارد می‌کند. اسکریپت `backend/app/utils/create_admin.py` نیز حساب مدیر را ایجاد می‌کند؛ قبلاً باید آن را دستی اجرا می‌کردید. اکنون اسکریپت شروع برنامه این مراحل را خودکار انجام می‌دهد.

در هر شروع کانتینر Backend:
1. پیکربندی و رمزهای ضروری اعتبارسنجی می‌شوند.
2. برنامه منتظر آماده‌شدن MySQL می‌ماند.
3. `alembic upgrade head` اجرا می‌شود.
4. مدیر اولیه مطابق مقادیر `.env` ایجاد می‌شود، اگر از قبل وجود نداشته باشد.
5. API اجرا می‌شود.

Migrationها و ساخت مدیر اولیه قابل تکرارند؛ داده‌های موجود حذف نمی‌شوند. از `docker compose down -v` در محیط دارای داده واقعی استفاده نکنید، چون volume دیتابیس را حذف می‌کند.

## راه‌اندازی روی سرور

### 1. ساخت فایل محیطی

از پوشه `project` اجرا کنید:

```bash
cp .env.example .env
nano .env
```

همه مقدارهای `REPLACE_WITH_...` را با رمزها و کلیدهای یکتای خودتان جایگزین کنید. رمز مدیر باید حداقل ۱۲ کاراکتر و دو کلید امضا باید حداقل ۳۲ کاراکتر باشند. برای سازگاری ساده‌تر با اتصال MySQL، برای رمز دیتابیس رشته تصادفی حروف و اعداد بسازید؛ نمونه تولید مقدار:

```bash
openssl rand -hex 32
```

برای هر متغیر محرمانه مقدار متفاوت تولید کنید. فایل واقعی `.env` در Git نادیده گرفته می‌شود؛ آن را commit نکنید و برای کسی نفرستید.

### 2. ساخت و اجرای سرویس‌ها

روی سرور Docker Engine و افزونه Docker Compose باید نصب باشند. در پوشه `project`:

```bash
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```

برای دیدن لاگ‌ها از ترمینال با `Ctrl+C` خارج شوید؛ این کار کانتینرها را متوقف نمی‌کند.

### 3. تنظیم DNS

در پنل DNS دامنه، رکورد `A` برای نام `task` بسازید که به IP عمومی سرور اشاره کند:

- نام/Host: `task`
- نوع: `A`
- مقدار: IP سرور

این تغییر فقط زیر دامنه `task.tinateck.ir` را هدف می‌گیرد. رکورد و کانفیگ دامنه اصلی `tinateck.ir` را برای این پروژه تغییر ندهید.

### 4. فعال‌سازی Nginx روی میزبان

فایل آماده در `deploy/nginx-task.tinateck.ir.conf` است. آن را در Nginx میزبان نصب کنید:

```bash
sudo cp deploy/nginx-task.tinateck.ir.conf /etc/nginx/sites-available/task.tinateck.ir
sudo ln -s /etc/nginx/sites-available/task.tinateck.ir /etc/nginx/sites-enabled/task.tinateck.ir
sudo nginx -t
sudo systemctl reload nginx
```

اگر لینک قبلاً وجود دارد، دوباره آن را نسازید. این فایل فقط پورت 80 را تنظیم می‌کند. پس از تنظیم DNS و تأیید دسترسی HTTP، برای HTTPS گواهی TLS صادر و فعال کنید؛ گواهی و DNS از داخل این مخزن قابل ایجاد نیستند.

### 5. بررسی اجرا

- سامانه: `http://task.tinateck.ir`
- سلامت API از داخل شبکه: `/health` روی Backend
- مستندات API: در حال حاضر Backend پورت میزبان ندارد؛ برای دسترسی عمومی به Swagger پورت 8000 را باز نکنید. در صورت نیاز، مسیر `/docs` را با سیاست دسترسی مناسب از Nginx منتشر کنید.

اولین ورود از نام کاربری و رمز تعیین‌شده در `.env` استفاده می‌کند. مقدار پیش‌فرض امنی برای رمز مدیر وجود ندارد؛ شروع سرویس با رمزهای نمونه رد می‌شود.

## ساختار مهم

- `backend/alembic/versions/`: migrationها و داده‌های اولیه مجوزها
- `backend/app/utils/create_admin.py`: ساخت مدیر اولیه
- `backend/app/utils/bootstrap.py`: آماده‌سازی دیتابیس و شروع API
- `docker-compose.yml`: MySQL، Backend و Frontend
- `frontend/nginx.conf`: سرویس‌دهی فرانت‌اند و پراکسی API
- `deploy/nginx-task.tinateck.ir.conf`: کانفیگ Nginx میزبان برای زیر دامنه

## توسعه

برای تغییر ساختار دیتابیس migration جدید بسازید؛ migration اولیه را برای دیتابیس‌هایی که قبلاً نصب شده‌اند بازنویسی نکنید. فایل `.env` و داده‌های کاربران را در Git قرار ندهید.
