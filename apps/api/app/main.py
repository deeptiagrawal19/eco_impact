import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import settings
from app.routers.carbon import router as carbon_router
from app.routers.dashboard import catalog_router, router as dashboard_router
from app.routers.impact import router as impact_router
from app.routers.reports import router as reports_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Eco Impact API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(carbon_router)
app.include_router(dashboard_router)
app.include_router(catalog_router)
app.include_router(impact_router)
app.include_router(reports_router)


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
