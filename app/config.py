from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import field_validator, model_validator
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

    # Camera-server (HLS streaming proxy). The Gateway calls
    # POST {camera_server_url}/spe-camera/api/open from /cameras/{id}/feed
    # to obtain an HLS URL for a client.
    camera_server_url: str = "http://localhost:8080"

    # Public-facing base URL prepended to the relative hls_url returned by
    # camera-server (e.g. "http://localhost:8080" for dev, or your nginx
    # public origin like "https://smart.damanat.com.sa" for production).
    # Empty → return relative URLs unchanged.
    camera_feed_public_base_url: str = ""

    # Optional path prefix inserted between the gateway origin and its route
    # paths in externally-facing URLs (embed links, etc.).  Useful when the
    # gateway sits behind a reverse proxy that strips a prefix, e.g.
    # GATEWAY_PATH_PREFIX=/api  →  https://host/api/cameras/{id}/feed/embed
    # Empty string (default) means no prefix.
    gateway_path_prefix: str = ""

    camera_monitor_enabled: bool = True
    camera_monitor_interval_seconds: int = 60
    camera_monitor_tcp_timeout_seconds: float = 3.0
    camera_monitor_concurrency: int = 20

    # Facility-local clock offset from UTC, applied to "today" / "since-local-midnight" computations.
    facility_timezone_offset_hours: float = 3.0

    # ── Reporting window (Report 1 / Occupancy & Utilization) ─────────────────
    # The hours the facility actually operates, in facility-local time. When
    # `report_business_hours_enabled` is on, occupancy percentages are computed
    # against `capacity x these hours x days` instead of a full 24 hours, so
    # empty overnight hours stop diluting the figure.
    #
    # Measured from this deployment's own data (Jul-Aug 2026): arrivals ramp at
    # 07:00, plateau ~75% between 11:00 and 15:00, and the garage has drained by
    # 18:00. That window holds 87.6% of all car-hours parked.
    #
    # `_to` is EXCLUSIVE — 7..18 means 07:00:00 through 17:59:59, i.e. 11 hours.
    #
    # NOTE: defaulting this to true DEPARTS from decision Q1 ("reporting window
    # is the full 24 hours"). Set REPORT_BUSINESS_HOURS_ENABLED=false to restore
    # the Q1 convention without a code change. All days of the week are counted;
    # the weekend shows as two low bars in the Mon-Sun trend chart rather than
    # being filtered out, so the KPI stays reconcilable with the chart below it.
    report_business_hours_enabled: bool = True
    report_business_hour_from: int = 7
    report_business_hour_to: int = 18

    # Days the facility operates, comma-separated (Mon Tue Wed Thu Fri Sat Sun,
    # case-insensitive). Days outside this list are dropped from the occupancy
    # denominators entirely — they are not "0% days", they are not-counted days.
    #
    # Default is ALL SEVEN, deliberately. This deployment's operating week is
    # Sun-Thu (Fri/Sat average 1.7 and 3.0 sessions vs ~26), and excluding them
    # lifts the KPI from 43.4% to 55.7% — but the Mon-Sun trend chart below the
    # KPI always renders seven bars (Q5), so the headline would no longer be the
    # average of the bars the operator can see. Counting all days keeps the two
    # reconcilable; the weekend simply shows as two low bars.
    #
    # To switch to the operating week: REPORT_BUSINESS_DAYS=Sun,Mon,Tue,Wed,Thu
    report_business_days: str = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"

    @field_validator("report_business_hour_from", "report_business_hour_to")
    @classmethod
    def _valid_hour(cls, v: int) -> int:
        # 24 is legal for `_to` only (means "to end of day"); guard the range so
        # a typo in .env fails at boot rather than silently zeroing a KPI.
        if not 0 <= v <= 24:
            raise ValueError("report business hours must be between 0 and 24")
        return v

    @model_validator(mode="after")
    def _valid_business_window(self):
        if self.report_business_hour_from >= self.report_business_hour_to:
            raise ValueError(
                "REPORT_BUSINESS_HOUR_FROM must be less than REPORT_BUSINESS_HOUR_TO"
            )
        # Parse eagerly so a typo ("Thur", "Sunday ") fails at boot with a clear
        # message, rather than silently shrinking every occupancy denominator.
        self.business_weekdays  # noqa: B018 — property raises on bad input
        return self

    @property
    def business_weekdays(self) -> frozenset[int]:
        """`report_business_days` as Python weekday ints (Mon=0 .. Sun=6),
        matching `datetime.date.weekday()`."""
        names = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
        parsed = set()
        for token in self.report_business_days.split(","):
            key = token.strip().lower()[:3]
            if not key:
                continue
            if key not in names:
                raise ValueError(
                    f"REPORT_BUSINESS_DAYS: unrecognised day {token.strip()!r} "
                    f"(expected any of Mon,Tue,Wed,Thu,Fri,Sat,Sun)"
                )
            parsed.add(names[key])
        if not parsed:
            raise ValueError("REPORT_BUSINESS_DAYS must list at least one day")
        return frozenset(parsed)

    # Where the PMS-AI snapshot files appear inside the gateway container.
    # Mount the same volume PMS-AI writes to (read-only). When the directory
    # exists, /snapshots is exposed as a StaticFiles mount and DTO snapshot_url
    # values are rewritten from `detection_images/foo.jpg` → `/snapshots/foo.jpg`.
    snapshots_local_dir: str = "/app/detection_images"
    # Optional absolute origin prefix for snapshot URLs; empty → same-origin.
    snapshots_public_base: str = ""
    # System 2 (VideoAnalytics) direct snapshot base URL.
    system2_snapshots_public_base: str = ""

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
    FACILITY_TIMEZONE_OFFSET_HOURS env var (default 3.0 = UTC+3, Saudi Arabia /
    Riyadh — no DST). The DB convention (since 2026-05-07) is naive
    facility-local — every writer stores the operator's wall clock, not UTC.
    Both the Gateway and PMS-AI must run with the same value to keep "today"
    windows aligned across services."""
    return timezone(timedelta(hours=settings.facility_timezone_offset_hours))


def facility_now_naive() -> datetime:
    """Current facility-local datetime, NAIVE (no tzinfo). Drop-in replacement
    for `datetime.utcnow()` / `datetime.now(UTC)` at every DB-write call site.
    Works regardless of host OS / container TZ — `datetime.now()` alone gives
    UTC on K8s pods running with TZ=UTC and silently lands rows 3h behind."""
    return datetime.now(facility_tz()).replace(tzinfo=None)


def localize_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """Attach facility-local tzinfo to a naive DB timestamp so it serialises
    with the correct UTC offset (e.g. +03:00) instead of being misread as UTC.
    Use only when the DB column is already facility-local-naive (the new convention
    since 2026-05-07). For UTC-naive columns written by PMS-AI (e.g. triggered_at,
    resolved_at in the alerts table), use utc_naive_to_local() instead."""
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=facility_tz())


def utc_naive_to_local(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert a UTC-naive DB timestamp to a facility-local-aware datetime."""
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc).astimezone(facility_tz())


def smart_localize(dt: Optional[datetime]) -> Optional[datetime]:
    """Auto-detect whether a naive timestamp is UTC or facility-local and return
    a facility-local-aware datetime.

    - Aware datetimes are converted to facility-local tz directly.
    - Naive datetimes: compared against datetime.utcnow() and facility_now_naive().
      Whichever the value is closest to is assumed to be its timezone.
      Reliable for events within ~90 min of now; older records near the
      FACILITY_TIMEZONE_OFFSET_HOURS boundary may occasionally misclassify."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(facility_tz())
    now_local = facility_now_naive()
    diff_local = abs((now_local - dt).total_seconds())
    diff_utc   = abs((datetime.utcnow() - dt).total_seconds())
    if diff_utc < diff_local:
        return dt.replace(tzinfo=timezone.utc).astimezone(facility_tz())
    return dt.replace(tzinfo=facility_tz())


def facility_today_utc() -> datetime:
    """[name kept for back-compat; semantics shifted 2026-05-07]
    Naive facility-local datetime of midnight today. Use this when filtering
    SQL columns (now stored facility-local-naive) for "since local midnight
    today". Returns naive — drop the tzinfo so it compares against naive
    DB values without raising mixed-tz comparison errors. Despite the name,
    no UTC is involved anymore."""
    now_local = datetime.now(facility_tz())
    midnight_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight_local.replace(tzinfo=None)