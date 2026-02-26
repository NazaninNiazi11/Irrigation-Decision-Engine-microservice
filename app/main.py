from fastapi import FastAPI
from app.interfaces.api import router

app = FastAPI(title="Irrigation Decision Engine")

app.include_router(router)