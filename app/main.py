from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import dashboard, alerts, entry_exit, vehicles, occupancy, camera_feeds, cameras
from app.services import camera_monitor


@asynccontextmanager
async def lifespan(app: FastAPI):
    camera_monitor.start()
    try:
        yield
    finally:
        await camera_monitor.stop()


app = FastAPI(
    title="Parking API Gateway",
    description="System 3 — the only API the frontend talks to.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    # Permissive localhost regex so any dev port (3000, 4200, 5173, 8080, …)
    # is accepted without having to maintain the explicit list. In production
    # only ALLOWED_ORIGINS matters — set it to your real frontend domain(s).
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(alerts.router)
app.include_router(entry_exit.router)
app.include_router(vehicles.router)
app.include_router(occupancy.router)
app.include_router(camera_feeds.router)
app.include_router(cameras.router)


@app.get("/health", tags=["Gateway"])
async def gateway_health():
    return {"status": "ok", "service": "API Gateway"}
