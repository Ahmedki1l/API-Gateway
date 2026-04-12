from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import dashboard, alerts, entry_exit, vehicles, occupancy

app = FastAPI(
    title="Parking API Gateway",
    description="System 3 — the only API the frontend talks to.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(alerts.router)
app.include_router(entry_exit.router)
app.include_router(vehicles.router)
app.include_router(occupancy.router)


@app.get("/health", tags=["Gateway"])
async def gateway_health():
    return {"status": "ok", "service": "API Gateway"}
