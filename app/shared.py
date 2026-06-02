"""
Shared utilities used by every router:
  - PagedResponse  : uniform { totalCount, page, pageSize, items } envelope
  - stream_csv     : streams a CSV file as a download response
  - plate search   : dash/space-insensitive plate matching helpers
"""
import csv
import io
import re
from typing import Any, Optional
from fastapi.responses import StreamingResponse


def normalize_plate_term(term: str) -> str:
    """Strip separators/whitespace and upper-case a plate search term so a
    full plate typed as "4918-AVD" (or "4918 AVD") compares apples-to-apples
    with a stored value regardless of how the dash/space was recorded.
    Upper-cased for parity with SQL Server's default CI collation."""
    return re.sub(r"[-\s]", "", term or "").upper()


def _swap_plate_order(core: str) -> Optional[str]:
    """Digit/letter-swapped form of a normalized plate core
    ("4918AVD" -> "AVD4918"), or None if it isn't a single digit-run +
    letter-run. The frontend displays plates in the reverse order from how
    they're stored, so the search must try both orders."""
    m = re.match(r"^(\d+)([A-Z]+)$", core)
    if m:
        return m.group(2) + m.group(1)
    m = re.match(r"^([A-Z]+)(\d+)$", core)
    if m:
        return m.group(2) + m.group(1)
    return None


def plate_search_clause(column: str, term: str, params: dict, prefix: str = "plate") -> str:
    """Build a dash/space- AND order-insensitive LIKE match for plate `column`,
    appending the bind params it needs to `params`.

    The DB stores plates in one digit/letter order and the frontend DISPLAYS
    them in the reverse order, so a full plate typed as shown on screen
    ("4918-AVD") must still match the stored value ("AVD-4918"). We strip
    separators from the stored column and match it against both the typed core
    and its swapped-order variant. A partial term (e.g. "4918") has nothing to
    swap and matches as a substring as before."""
    core = normalize_plate_term(term)
    variants = [core]
    swapped = _swap_plate_order(core)
    if swapped and swapped != core:
        variants.append(swapped)
    col_expr = f"REPLACE(REPLACE({column}, '-', ''), ' ', '')"
    ors = []
    for i, variant in enumerate(variants):
        name = f"{prefix}{i}"
        params[name] = f"%{variant}%"
        ors.append(f"{col_expr} LIKE :{name}")
    return "(" + " OR ".join(ors) + ")"


def build_paged(items: list[Any], total: int, page: int, page_size: int) -> dict:
    return {
        "total_count": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


def stream_csv(rows: list[dict], headers: list[str], filename: str) -> StreamingResponse:
    """
    Streams rows as a downloadable CSV file.
    rows  : list of dicts (keys must match headers exactly, case-insensitive)
    headers : ordered column names for the CSV header row
    """
    def generate():
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        for row in rows:
            # normalise key casing so dict keys don't have to match exactly
            normalised = {k.lower(): v for k, v in row.items()}
            out = {h: normalised.get(h.lower(), "") for h in headers}
            writer.writerow(out)
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
