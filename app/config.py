from datetime import datetime, timedelta, timezone

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_driver: str = "ODBC Driver 18 for SQL Server"
    db_server: str = "localhost"
    db_port: int = 1433
    db_name: str = "damanat_pms"
    db_user: str = "sa"
    db_password: str = "YourStrong!Pass1"
    db_trusted_connection: bool = False

    system1_base_url: str = "http://localhost:8080"
    system2_base_url: str = "http://localhost:8000"

    gateway_port: int = 8001
    allowed_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:4200"

    cameras_encryption_key: str
    cameras_internal_token: str

    camera_monitor_enabled: bool = True
    camera_monitor_interval_seconds: int = 60
    camera_monitor_tcp_timeout_seconds: float = 3.0
    camera_monitor_concurrency: int = 20

    # Facility-local clock offset from UTC, applied to "today" / "since-local-midnight" computations.
    facility_timezone_offset_hours: float = 2.0

    @property
    def db_connection_string(self) -> str:
        # Local-dev fallback: DB_DRIVER=pymssql (FreeTDS-based, no system ODBC required)
        if self.db_driver.lower() == "pymssql":
            return (
                f"mssql+pymssql://{self.db_user}:{self.db_password}"
                f"@{self.db_server}:{self.db_port}/{self.db_name}"
            )

        driver = self.db_driver.replace(" ", "+")

        if self.db_trusted_connection:
            # Windows authentication. The empty `@` between the scheme and the
            # host tells SQLAlchemy/pyodbc not to attempt SQL auth — without it
            # the driver can fail with "Login failed for user ''" on some boxes.
            # Capitalisation matches the ODBC documented spelling.
            return (
                f"mssql+pyodbc://@{self.db_server}:{self.db_port}/{self.db_name}"
                f"?driver={driver}&Trusted_Connection=Yes&TrustServerCertificate=Yes"
            )

        return (
            f"mssql+pyodbc://{self.db_user}:{self.db_password}"
            f"@{self.db_server}:{self.db_port}/{self.db_name}"
            f"?driver={driver}&TrustServerCertificate=Yes"
        )

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def facility_tz() -> timezone:
    """The local timezone for "today"-style date math. Configurable via
    FACILITY_TIMEZONE_OFFSET_HOURS env var (default UTC+2 for the current
    Riyadh-region deployment)."""
    return timezone(timedelta(hours=settings.facility_timezone_offset_hours))


def facility_today_utc() -> datetime:
    """UTC instant of facility-local midnight today. Use this when filtering
    SQL columns stored in UTC to "since local midnight today"."""
    now_local = datetime.now(facility_tz())
    midnight_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight_local.astimezone(timezone.utc)