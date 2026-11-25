import os
import sys
import asyncio
from pathlib import Path

# On Windows, Playwright requires ProactorEventLoop for subprocesses
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from backend.config import settings, SCREENSHOTS_DIR
from backend.routes import inspections, issues, repairs

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="OmniSight AI-Powered Website Inspection & Self-Healing Backend"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Screenshots Mount
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")

# Routers
app.include_router(inspections.router)
app.include_router(issues.router)
app.include_router(repairs.router)

@app.get("/api/health")
async def health_check():
    gemini_configured = bool(settings.gemini_api_key or os.getenv("GEMINI_API_KEY"))
    openai_configured = bool(settings.openai_api_key or os.getenv("OPENAI_API_KEY"))
    github_configured = bool(settings.github_token or os.getenv("GITHUB_TOKEN"))
    
    return {
        "status": "healthy",
        "service": "OmniSight Backend",
        "version": settings.version,
        "playwright": "ready",
        "ai_vision_provider": "gemini" if gemini_configured else "openai" if openai_configured else "rule_based_fallback",
        "gemini_configured": gemini_configured,
        "openai_configured": openai_configured,
        "github_configured": github_configured,
        "screenshots_directory": str(SCREENSHOTS_DIR)
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": f"Internal server error: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.api_host, port=settings.api_port, reload=True)
