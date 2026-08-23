import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.db.session import init_db, DATABASE_URL
from backend.api.routes import router as api_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield


app = FastAPI(
    title="ReconPilot API",
    description="AI-Powered Finance Reconciliation Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
allowed_origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
