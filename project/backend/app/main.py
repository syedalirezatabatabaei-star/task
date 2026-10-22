from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.api import auth, users, permissions, projects, stages, tasks, evaluations, attachments, dashboard, reports, audit

app = FastAPI(
    title=settings.APP_NAME,
    description="سیستم مدیریت کارآموزی و پروژه",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount uploads for static file serving
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# API v1 routers
PREFIX = "/api/v1"

app.include_router(auth.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(permissions.router, prefix=PREFIX)
app.include_router(projects.router, prefix=PREFIX)
app.include_router(stages.router, prefix=PREFIX)
app.include_router(tasks.router, prefix=PREFIX)
app.include_router(evaluations.router, prefix=PREFIX)
app.include_router(attachments.router, prefix=PREFIX)
app.include_router(dashboard.router, prefix=PREFIX)
app.include_router(reports.router, prefix=PREFIX)
app.include_router(audit.router, prefix=PREFIX)


@app.get("/", tags=["Health"])
def root():
    return {"message": "سیستم مدیریت کارآموزی", "status": "running", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"success": False, "message": "آدرس مورد نظر یافت نشد", "code": "NOT_FOUND"},
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "خطای داخلی سرور", "code": "INTERNAL_ERROR"},
    )
