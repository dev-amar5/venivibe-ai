from fastapi import APIRouter, Depends, Query
from db import get_db_session
from src.apps.admin.services.admin_notifications import *

router = APIRouter(prefix="/notifications", tags=["notifications"])

class AlertResponse(BaseModel):
    id: UUID
    alert_type: str
    organizer_id: Optional[UUID] = None
    event_id: Optional[UUID] = None
    organizer_name: Optional[str] = None
    event_name: Optional[str] = None
    alert_title: str
    alert_description: str
    refund_count: Optional[int] = None
    login_fail_count: Optional[int] = None
    ticket_price: Optional[float] = None
    is_first_time: Optional[bool] = None
    risk_score: Optional[int] = None
    risk_category: Optional[str] = None


@router.get("/alerts/{alert_id}")
def alert_detail(alert_id: str, db: Session = Depends(get_db_session)):
    data = get_alert_details(alert_id, db)
    if not data:
        raise HTTPException(status_code=404, detail="Alert not found")

    return data
    return data
    # return AlertRiskResponse(**data)

@router.post("/alerts/{alert_id}/investigate")
def investigate_further():
    return {"message": "This API is not implemented yet"}

@router.post("/alerts/{alert_id}/escalate")
def button_action_stub():
    return {"message": "This API is not implemented yet"}

@router.get("/alerts")
def list_alerts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: Optional[int] = Query(None, description="Number of records to return (omit to return all)"),
    alert_type: Optional[AlertType] = Query(None, description="Filter by alert type"),
    risk_category: Optional[RiskCategory] = Query(None, description="Filter by risk category"),
    duration_hours: Optional[int] = Query(None, ge=1, le=168, description="Filter alerts created in the last N hours (e.g., 1, 12, 24)"),
    popup: bool = Query(False, description="If true, return unseen alert (limit 1)"),
    db: Session = Depends(get_db_session),
):
    alerts = fetch_alerts(
        db=db,
        skip=skip,
        limit=limit,
        alert_type=alert_type,
        risk_category=risk_category,
        duration_hours=duration_hours,
        popup=popup,
    )

    if not alerts:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alerts



@router.patch("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, db: Session = Depends(get_db_session)):
    """API endpoint to mark an alert as resolved."""
    return mark_alert_as_resolved(db, alert_id)

@router.patch("/alerts/{alert_id}/flag")
def flag_alert(alert_id: UUID, db: Session = Depends(get_db_session)):
    """API endpoint to mark an alert as resolved."""
    return mark_alert_as_flagged(db, alert_id)

@router.patch("/alerts/{alert_id}/seen")
def flag_alert(alert_id: UUID, db: Session = Depends(get_db_session)):
    """API endpoint to mark an alert as resolved."""
    return mark_alert_as_is_seen(db, alert_id)

if __name__ == "__main__":
    pass






