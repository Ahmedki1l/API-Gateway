"""Report pages whose numbers mix sources, so no single tab router owns them."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers._helpers import resolve_floor_id
from app.routers.alerts import _alerts_extra_cols, _summary_by_type, _where as _alert_where
from app.routers.entry_exit import overstay_count
from app.schemas import OverstayViolationsReport
from app.schemas_enums import AlertSeverity

from app.routers.prefix_injection import (get_prefix)
# Lives under /alerts: the report is an alerts view (plus derived overstays).
prefix = get_prefix() + "/alerts/reports"

router = APIRouter(prefix=prefix, tags=["Alerts"])


@router.get("/overstay-violations", response_model=OverstayViolationsReport)
async def overstay_violations_report(
    date_from: Optional[date] = Query(None, description="First day (inclusive), facility-local. Omit both for all time."),
    date_to: Optional[date] = Query(None, description="Last day (inclusive), facility-local."),
    severity: Optional[AlertSeverity] = Query(None, description="Alerts only."),
    floor: Optional[str] = Query(None),
    floor_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, description="Alerts: plate / slot / zone / description. Overstays: plate."),
    db: Session = Depends(get_db),
):
    """Overstay & Violations report — the Total Violations card and the
    breakdown beside it.

    - `overstays`: distinct cars that were inside the garage at a local
      midnight in the range, from parking_sessions. The same number as the
      Entry/Exit Overstays card for the same dates. Overstay is not an alert:
      nothing writes one (Damanat-DB-Migrator 0010), so it is never in `by_type`.
    - `by_type` / `alerts_total`: every alert TRIGGERED in the range, resolved
      since or not, by type — the same slices as /alerts/summary.
    - `total_violations` = `overstays` + `alerts_total`.
    """
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must not be after date_to")
    cols = _alerts_extra_cols()
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=floor)
    where, params = _alert_where(
        search, severity, None, None, date_from, date_to, cols,
        floor_id=resolved_floor_id, floor=floor,
    )
    # A stray row named "overstay" must not count twice.
    where += " AND a.alert_type <> 'overstay'"
    alerts_total, by_type = _summary_by_type(db, where, params, cols)
    # Without dbo.alert_types the built-in type list names `overstay` too.
    by_type = [t for t in by_type if t.alert_type != "overstay"]

    overstays = overstay_count(db, date_from, date_to, floor=floor, floor_id=resolved_floor_id, search=search)
    return OverstayViolationsReport(
        date_from=date_from,
        date_to=date_to,
        total_violations=overstays + alerts_total,
        overstays=overstays,
        alerts_total=alerts_total,
        by_type=by_type,
    )
