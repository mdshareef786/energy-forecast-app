from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.database import Base, engine
import app.models  # noqa: F401 - ensures all models are registered on Base.metadata

from app.api.routes import (
    auth, assets, datasets, forecasts, anomalies, recommendations,
    simulations, analytics, alerts, reports,
)
from app.services.retraining import start_scheduler, shutdown_scheduler

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler(interval_hours=24)
    yield
    shutdown_scheduler()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(assets.router)
app.include_router(datasets.router)
app.include_router(forecasts.router)
app.include_router(anomalies.router)
app.include_router(recommendations.router)
app.include_router(simulations.router)
app.include_router(analytics.router)
app.include_router(alerts.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.get("/health")
def health():
    return {"status": "healthy"}
