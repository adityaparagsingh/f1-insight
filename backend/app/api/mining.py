"""Data-mining endpoints: clustering, prediction, association, classification."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.mining import association, classification, clustering, prediction

router = APIRouter(prefix="/mining", tags=["data-mining"])


@router.get("/clusters", summary="K-Means driver performance clustering")
def clusters(
    k: Optional[int] = Query(None, ge=2, le=8,
                             description="Force k; omit to auto-select (elbow+silhouette)"),
    min_races: int = Query(15, ge=5, le=100,
                           description="Minimum career races per driver"),
    force: bool = Query(False, description="Recompute instead of using cache"),
    db: Session = Depends(get_db),
) -> dict:
    return clustering.run_clustering(db, k=k, min_races=min_races, force=force)


@router.get("/prediction", summary="Race winner prediction (pre-race features only)")
def prediction_endpoint(
    train_until: Optional[int] = Query(
        None, ge=1950, le=2100,
        description="Train on seasons <= this year (default: two seasons before latest)"),
    force: bool = Query(False, description="Recompute instead of using cache"),
    db: Session = Depends(get_db),
) -> dict:
    return prediction.run_prediction(db, train_until=train_until, force=force)


@router.get("/association-rules", summary="Apriori association rule mining")
def association_rules(
    min_support: float = Query(0.03, ge=0.001, le=0.5),
    min_confidence: float = Query(0.4, ge=0.05, le=1.0),
    min_lift: float = Query(1.05, ge=0.0, le=10.0),
    force: bool = Query(False, description="Recompute instead of using cache"),
    db: Session = Depends(get_db),
) -> dict:
    return association.run_association(
        db, min_support=min_support, min_confidence=min_confidence,
        min_lift=min_lift, force=force,
    )


@router.get("/classification", summary="Performance classification (documented formula)")
def classification_endpoint(
    season: Optional[int] = Query(None, ge=1950, le=2100),
    force: bool = Query(False, description="Recompute instead of using cache"),
    db: Session = Depends(get_db),
) -> dict:
    return classification.run_classification(db, season=season, force=force)
