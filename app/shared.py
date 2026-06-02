"""
Shared utilities used by every router:
  - PagedResponse  : uniform { totalCount, page, pageSize, items } envelope
  - stream_csv     : streams a CSV file as a download response
  - plate search   : dash/space-insensitive plate matching helpers
"""
import csv
import io
import re
from typing import Any
from fastapi.responses import StreamingResponse


def normalize_plate_term(term: str) -> str:
    """Strip separators/whitespace from a free-text plate search term so a
    full plate typed as "4918-AVD" (or "4918 AVD") matches a stored value
    regardless of how the dash/space was recorded. Upper-cased for parity
    with the SQL Server default case-insensitive collation."""
    return re.sub(r"[-\s]", "", term or "").upper()


def plate_search_sql(column: str, param: str) -> str:
    """SQL fragment matching `column` against a normalized plate search term.
    Strips dashes and spaces from the STORED value so the comparison is
    apples-to-apples with a term normalized via `normalize_plate_term`.
    Bind `:{param}` to `f"%{normalize_plate_term(term)}%"`.

    Fixes the bug where searching the full plate "4918-AVD" returned nothing
    while the prefix "4918" matched — the stored value did not contain the
    dash in the same position the user typed it."""
    return f"REPLACE(REPLACE({column}, '-', ''), ' ', '') LIKE :{param}"


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
