"""
Admin creation utility.
Usage: python -m app.utils.create_admin

Reads from environment variables:
  ADMIN_USERNAME
  ADMIN_PASSWORD
  ADMIN_FIRST_NAME
  ADMIN_LAST_NAME
  ADMIN_EMAIL
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


def create_admin():
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    first_name = os.environ.get("ADMIN_FIRST_NAME", "مدیر")
    last_name = os.environ.get("ADMIN_LAST_NAME", "سیستم")
    email = os.environ.get("ADMIN_EMAIL")

    if not username or not password:
        print("خطا: متغیرهای ADMIN_USERNAME و ADMIN_PASSWORD باید تنظیم شوند.")
        print("مثال:")
        print("  $env:ADMIN_USERNAME='admin'")
        print("  $env:ADMIN_PASSWORD='yourpassword'")
        sys.exit(1)

    if len(password) < 8:
        print("خطا: رمز عبور باید حداقل ۸ کاراکتر باشد.")
        sys.exit(1)

    if len(password.encode("utf-8")) > 72:
        print("خطا: رمز عبور برای الگوریتم bcrypt نباید بیشتر از ۷۲ بایت باشد. مقدار ADMIN_PASSWORD را در فایل .env کوتاه‌تر کنید.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            if existing.role == UserRole.ADMIN:
                print(f"کاربر مدیر '{username}' قبلاً وجود دارد.")
            else:
                print(f"کاربر '{username}' وجود دارد اما مدیر نیست. در حال ارتقا...")
                existing.role = UserRole.ADMIN
                existing.is_active = True
                db.commit()
                print(f"کاربر '{username}' به مدیر ارتقا یافت.")
            return

        admin = User(
            username=username,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"✓ کاربر مدیر '{username}' با موفقیت ایجاد شد (ID: {admin.id})")
        print("لطفاً رمز عبور را در مکان امنی ذخیره کنید.")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
