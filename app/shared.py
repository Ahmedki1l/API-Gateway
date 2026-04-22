"""
Shared utilities used by every router:
  - PagedResponse  : uniform { totalCount, page, pageSize, items } envelope
  - stream_csv     : streams a CSV file as a download response
"""
import csv
import io
from typing import Any
from fastapi.responses import StreamingResponse



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
