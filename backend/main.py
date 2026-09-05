import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure repository root is on sys.path so 'backend.*' imports succeed regardless of working directory
REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.db.session import init_db, DATABASE_URL
from backend.api.routes import router as api_router
from backend.api.rate_limiter import RateLimiterMiddleware
from backend.logging_config import get_logger

load_dotenv()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    logger.info("Initializing database schema...")
    init_db()
    logger.info("ReconPilot API ready to accept requests.")
    yield
    logger.info("ReconPilot API shutting down.")


app = FastAPI(
    title="ReconPilot API",
    description="AI-Powered Finance Reconciliation Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate Limiter Middleware (120 req/min)
app.add_middleware(RateLimiterMiddleware, max_requests=120, window_seconds=60)

# CORS configuration
origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
allowed_origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CSRF Protection Note (M4):
# ReconPilot utilizes stateless Bearer token and API key headers for authentication.
# In accordance with OWASP API Security guidelines, CSRF protection is not applicable
# because credentials are not automatically transmitted via ambient browser cookies.
# If session cookie-based authentication is ever introduced, CSRF token middleware must be mounted.

# Mount API router
app.include_router(api_router)


@app.get("/health")
def root_health():
    """Root health check route for load balancers and frontend probes."""
    return {
        "status": "healthy",
        "service": "ReconPilot Backend",
        "version": "1.0.0",
        "database_type": "postgresql" if "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL else "sqlite",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
