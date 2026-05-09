import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database.connection import engine, Base
from app.interfaces.api import router
from app.interfaces.auth_routes import auth_router
from app.rate_limit import limiter

# Import models so Base.metadata knows about them
from app.models import models  # noqa: F401
from app.database.seed import seed_db
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("irrigation")

INSECURE_SECRET_KEYS = {"", "dev-secret-key-change-in-production", "replace-me-with-a-strong-random-value"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    secret_key = os.getenv("SECRET_KEY", "")
    if secret_key in INSECURE_SECRET_KEYS:
        raise RuntimeError(
            "SECRET_KEY is missing or set to an insecure default. "
            "Set SECRET_KEY to a strong random value in your .env file. "
            "Generate one with: openssl rand -hex 32"
        )
    Base.metadata.create_all(bind=engine)

    print("seeding db")
    seed_db()

    yield


app = FastAPI(
    title="Irrigation Decision Engine",
    description="Analyzes soil and environmental data to calculate crop water stress and provide irrigation recommendations.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={"detail": "Database constraint violated. Check that values are unique and reference valid records."},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred. Please try again."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(auth_router)
app.include_router(router)
