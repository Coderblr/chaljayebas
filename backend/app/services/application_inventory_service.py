import json
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.misc import ApplicationInventory


def get_inventory_summary(db: Session, project_id: int) -> list[dict]:
    """Returns every screen Application Explorer has discovered for this project, oldest first,
    each with its real (live-crawled) URL and form fields - used to ground Page Object
    generation in real data instead of AI guesses from the requirement document alone."""

    rows = (
        db.query(ApplicationInventory)
        .filter(ApplicationInventory.project_id == project_id)
        .order_by(ApplicationInventory.discovered_at.asc())
        .all()
    )
    return [
        {
            "screen_name": row.screen_name,
            "url": row.url,
            "fields": json.loads(row.fields_json) if row.fields_json else [],
        }
        for row in rows
    ]


def get_discovered_base_url(db: Session, project_id: int) -> str | None:
    """The origin (scheme+host+port) of the earliest screen discovered for this project - in
    practice the login/start page Application Explorer was first pointed at, which is exactly
    what a generated framework's base.url should be."""

    first_row = (
        db.query(ApplicationInventory)
        .filter(ApplicationInventory.project_id == project_id, ApplicationInventory.url.isnot(None))
        .order_by(ApplicationInventory.discovered_at.asc())
        .first()
    )
    if first_row is None or not first_row.url:
        return None
    parsed = urlparse(first_row.url)
    return f"{parsed.scheme}://{parsed.netloc}"
