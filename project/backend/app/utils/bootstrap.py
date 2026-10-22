"""Production startup: validate configuration, wait for MySQL, migrate, seed the admin, run API."""
import os
import subprocess
import sys
import time

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv("/app/.env")

REQUIRED = ("SECRET_KEY", "JWT_SECRET_KEY", "MYSQL_ROOT_PASSWORD", "MYSQL_PASSWORD", "ADMIN_USERNAME", "ADMIN_PASSWORD")
PLACEHOLDERS = {"change-me", "change-me-admin-password", "change-me-to-a-long-random-string", "change-me-to-another-long-random-string", "rootpassword"}

def validate_environment() -> None:
    missing = [name for name in REQUIRED if not os.getenv(name, "").strip()]
    if missing:
        raise SystemExit("Missing required environment variables: " + ", ".join(missing))
    weak = [name for name in REQUIRED if os.getenv(name, "").strip().lower() in PLACEHOLDERS or os.getenv(name, "").strip().upper().startswith("REPLACE_WITH_")]
    if weak:
        raise SystemExit("Replace placeholder values in .env before starting: " + ", ".join(weak))
    if len(os.environ["ADMIN_PASSWORD"]) < 12:
        raise SystemExit("ADMIN_PASSWORD must contain at least 12 characters in production.")
    if len(os.environ["SECRET_KEY"]) < 32 or len(os.environ["JWT_SECRET_KEY"]) < 32:
        raise SystemExit("SECRET_KEY and JWT_SECRET_KEY must each contain at least 32 characters.")

def wait_for_database() -> None:
    from app.core.config import settings
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    last_error = None
    for attempt in range(1, 61):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            engine.dispose()
            print("Database is ready.", flush=True)
            return
        except Exception as exc:
            last_error = exc
            print(f"Waiting for MySQL ({attempt}/60)...", flush=True)
            time.sleep(3)
    engine.dispose()
    raise SystemExit(f"Database did not become ready: {last_error}")

def run() -> None:
    validate_environment()
    wait_for_database()
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    subprocess.run([sys.executable, "-m", "app.utils.create_admin"], check=True)
    os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])

if __name__ == "__main__":
    run()
