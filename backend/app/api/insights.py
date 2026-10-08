"""GET /api/insights — dynamically generated findings."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.insights import generate_insights

router = APIRouter(tags=["insights"])


@router.get("/insights", summary="Dynamically computed insights")
def insights(
    force: bool = Query(False, description="Recompute instead of using cache"),
    db: Session = Depends(get_db),
) -> dict:
    items = generate_insights(db, force=force)
    return {"count": len(items), "items": items}
