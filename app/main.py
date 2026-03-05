from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.database.connection import engine, Base
from app.interfaces.api import router

# Import models so Base.metadata knows about them
from app.models import models  # noqa: F401

from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    #Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Irrigation Decision Engine",
    description="Analyzes soil and environmental data to calculate crop water stress and provide irrigation recommendations.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
