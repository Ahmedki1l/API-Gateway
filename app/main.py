from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.database import engine
from app.routers import dashboard, alerts, entry_exit, vehicles, occupancy, camera_feeds

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
app.include_router(camera_feeds.router)


@app.on_event("startup")
def verify_database_connection() -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        raise RuntimeError(
            "Database connection failed at startup. Check DB_SERVER/DB_INSTANCE/DB_PORT and SQL Server availability."
        ) from exc


@app.exception_handler(OperationalError)
async def handle_db_operational_error(_, __):
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database is unavailable. Verify SQL Server is running and connection settings are correct."
        },
    )


@app.get("/health", tags=["Gateway"])
async def gateway_health():
    return {"status": "ok", "service": "API Gateway"}
