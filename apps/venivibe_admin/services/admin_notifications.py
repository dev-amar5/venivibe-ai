from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import SessionLocal
from apps.venivibe_admin.services.utils import load_config
from apps.venivibe_admin.schemas.admin_notifications import *

# ==============================
# Load Risk Score Config
# ==============================
risk_scores_config = load_config("risk_score_config.json")


# ==============================
# Risk Score Calculation
# ==============================
def calculate_risk_score_numeric(
    alert_type: str,
    numeric_value: float,
    context_conditions: list = []
) -> dict:
    alerts_config = risk_scores_config.get("alerts", {})
    context_modifiers = risk_scores_config.get("context_modifiers", {})

    alert = alerts_config.get(alert_type)
    if not alert:
        return {"risk_score": 0, "risk_category": "Low"}

    base_weight = alert["base_weight"]

    # Determine severity multiplier
    severity_score = 1
    for sev in sorted(alert["severity"], key=lambda x: x["threshold"], reverse=True):
        if numeric_value >= sev["threshold"]:
            severity_score = sev["multiplier"]
            break

    # Apply context modifiers
    context_score = 1
    for cond in context_conditions:
        context_score *= context_modifiers.get(cond, 1)

    # Compute risk score
    risk_score = min(base_weight * severity_score * context_score, 100)
    if risk_score < 50:
        risk_category = "Low"
    elif risk_score < 75:
        risk_category = "Moderate"
    else:
        risk_category = "High"

    return {"risk_score": risk_score, "risk_category": risk_category}


# ==============================
# Alert Detection Functions
# ==============================
def detect_multiple_login_fails(
    db: Session, threshold: int = 2, hours: int = 0.5
) -> List[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    results = db.execute(
        text("""
            SELECT ua.user_id, org.id AS organizer_id, COUNT(*) AS fail_count
            FROM user_activities ua
            JOIN organizers org ON ua.user_id = org.user_id
            WHERE ua.action_type = 'Login Failed'
            AND ua.created_at > :since
            GROUP BY ua.user_id, org.id
            HAVING COUNT(*) > :threshold
        """),
        {"since": since, "threshold": threshold}
    ).fetchall()

    notifications = []
    for user_id, organizer_id, fail_count in results:
        risk_obj = calculate_risk_score_numeric(
            alert_type="Multiple Failed Logins",
            numeric_value=fail_count
        )
        event = {
            "user_id": user_id,
            "organizer_id": organizer_id,
            "login_fail_count": fail_count,
            "alert_type": "Multiple Failed Logins",
            **risk_obj
        }
        notifications.append(AdminAlert(**event).model_dump())
    return notifications


def detect_mass_refunds(
    db: Session, threshold: int = 20, hours: int = 24
) -> List[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    results = db.execute(
        text("""
            SELECT 
    o.user_id,
    o.event_id,
    o.organizer_id,
    SUM(CASE WHEN o.status = '5' THEN pt.quantity ELSE 0 END) * 100.0 / SUM(pt.quantity) AS refund_rate,
    SUM(CASE WHEN o.status = '5' THEN pt.quantity ELSE 0 END) AS refund_count
FROM orders o
JOIN purchased_tickets pt ON o.id = pt.order_id
WHERE o.created_at > :since   
GROUP BY o.user_id, o.event_id, o.organizer_id
HAVING 
    (SUM(CASE WHEN o.status = '5' THEN pt.quantity ELSE 0 END) * 100.0 / SUM(pt.quantity)) >= :threshold;
        """),
        {"threshold": threshold, "since":since}
    ).fetchall()

    notifications = []
    for user_id, event_id, organizer_id, refund_rate, refund_count in results:
        risk_obj = calculate_risk_score_numeric(
            alert_type="Mass Refund",
            numeric_value=refund_rate
        )
        event = {
            "user_id": user_id,
            "event_id": event_id,
            "organizer_id": organizer_id,
            "refund_count": refund_count,
            "alert_type": "Mass Refund",
            **risk_obj
        }
        notifications.append(AdminAlert(**event).model_dump())
    return notifications


def detect_high_value_event(
    db: Session, hours: int = 24
) -> List[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    results = db.execute(
        text("""
            SELECT e.id AS event_id, e.organizer_id,
                   CASE WHEN e.created_at = FIRST_VALUE(e.created_at)
                        OVER (PARTITION BY e.organizer_id ORDER BY e.created_at ASC)
                        THEN TRUE ELSE FALSE END AS is_first_time,
                   tt.price
            FROM events e
            JOIN (
                SELECT DISTINCT ON (tt.event_id) tt.event_id, tt.price, tt.created_at
                FROM ticket_types tt
                ORDER BY tt.event_id, tt.created_at ASC
            ) tt ON e.id = tt.event_id
            WHERE e.created_at >= :since
        """),
        {"since": since}
    ).fetchall()

    notifications = []
    for event_id, organizer_id, is_first_time, price in results:
        risk_obj = calculate_risk_score_numeric(
            alert_type="New High-Value Event",
            numeric_value=price,
            context_conditions=["FirstTimeOrganizer"] if is_first_time else []
        )
        event = {
            "event_id": event_id,
            "organizer_id": organizer_id,
            "ticket_price": price,
            "alert_type": "New High-Value Event",
            "is_first_time": is_first_time,
            **risk_obj
        }
        notifications.append(AdminAlert(**event).model_dump())
    return notifications


def detect_suspicious_bulk_purchase(
    db: Session, threshold: int = 10, hours: int = 6
) -> List[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    results = db.execute(
        text("""
            SELECT user_id, event_id, organizer_id, SUM(quantity) AS ticket_quantity
            FROM orders o
            JOIN purchased_tickets pt ON o.id = pt.order_id
            WHERE pt.created_at > :since
            GROUP BY user_id, event_id, organizer_id
            HAVING SUM(quantity) >= :threshold
        """),
        {"since": since, "threshold": threshold}
    ).fetchall()

    notifications = []
    for user_id, event_id, organizer_id, ticket_quantity in results:
        risk_obj = calculate_risk_score_numeric(
            alert_type="Suspicious Bulk Purchase",
            numeric_value=ticket_quantity
        )
        event = {
            "user_id": user_id,
            "event_id": event_id,
            "organizer_id": organizer_id,
            "ticket_quantity": ticket_quantity,
            "alert_type": "Suspicious Bulk Purchase",
            **risk_obj
        }
        notifications.append(AdminAlert(**event).model_dump())
    return notifications


def detect_combined_alerts(db: Session) -> List[dict]:
    """Combine multiple alert detection functions."""
    return (
        detect_high_value_event(db)
        + detect_multiple_login_fails(db)
        + detect_mass_refunds(db)
        + detect_suspicious_bulk_purchase(db)
    )


# ==============================
# Alert Persistence
# ==============================
def save_alert(db: Session, alert: dict):
    """Insert or update alert in database."""
    try:
        db.execute(
            text("""
                INSERT INTO public.admin_alerts (
                    alert_type, user_id, event_id, organizer_id, refund_count, 
                    login_fail_count, ticket_price, ticket_quantity, is_first_time, 
                    risk_score, risk_category
                )
                VALUES (
                    :alert_type, :user_id, :event_id, :organizer_id, :refund_count, 
                    :login_fail_count, :ticket_price, :ticket_quantity, :is_first_time, 
                    :risk_score, :risk_category
                )
                ON CONFLICT (alert_type, event_id, organizer_id) DO UPDATE SET
                    refund_count = EXCLUDED.refund_count,
                    risk_score = EXCLUDED.risk_score,
                    updated_at = NOW()
                WHERE admin_alerts.risk_score IS DISTINCT FROM EXCLUDED.risk_score;
            """),
            {
                "alert_type": alert.get("alert_type"),
                "user_id": alert.get("user_id"),
                "event_id": str(alert.get("event_id")) if alert.get("event_id") else None,
                "organizer_id": str(alert.get("organizer_id")) if alert.get("organizer_id") else None,
                "risk_score": alert.get("risk_score"),
                "risk_category": alert.get("risk_category"),
                "refund_count": alert.get("refund_count"),
                "login_fail_count": alert.get("login_fail_count"),
                "ticket_price": alert.get("ticket_price"),
                "ticket_quantity": alert.get("ticket_quantity"),
                "is_first_time": alert.get("is_first_time"),
            }
        )
        db.commit()
    except Exception as e:
        print(f"Error saving alert: {e}")


# ==============================
# Alert Response Builders
# ==============================
ALERT_TITLES = {
    "Multiple Failed Logins": "Mass Failed Login Attempts",
    "Mass Refund": "Bulk Refund Spike",
    "Suspicious Bulk Purchase": "Suspicious Bulk Purchase Activity",
    "New High-Value Event": "High-Value Event Created",
}


def build_alert_response(alert: dict) -> AlertResponse:
    alert_type = alert.get("alert_type")
    alert_title = ALERT_TITLES.get(alert_type, "Unknown Alert Type")

    if alert_type == "Multiple Failed Logins":
        count = alert.get("login_fail_count", 0)
        base = (count // 10) * 10
        desc = f"{base if count % 10 == 0 else f'+{base}'} failed login attempts"

    elif alert_type == "New High-Value Event":
        price = alert.get("ticket_price", 0)
        base = (price // 500) * 500
        desc = f"New organizer created an event with tickets priced at ${base if price % 500 == 0 else f'+{base}'}"

    elif alert_type == "Mass Refund":
        event_name = alert.get('event_name', 'Unknown')
        desc = f"Multiple refunds processed in short timeframe for event '{event_name}'"

    elif alert_type == "Suspicious Bulk Purchase":
        ticket_quantity = alert.get("ticket_quantity", 0)
        event_name = alert.get('event_name', 'Unknown')
        desc = f"User purchased {ticket_quantity} tickets for event '{event_name}'"

    else:
        desc = f"Alert triggered for {alert_type}"

    merged = dict(alert)
    merged.update({"alert_title": alert_title, "alert_description": desc})
    return AlertResponse(**merged)

def fetch_alerts(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    alert_type: Optional[AlertType] = None,
    risk_category: Optional[RiskCategory] = None,
    duration_hours: Optional[int] = None,
    popup:bool = False,
):
    query = """
        SELECT 
            aa.id, aa.alert_type, aa.event_id, aa.organizer_id, 
            aa.refund_count, aa.login_fail_count, aa.ticket_price, 
            aa.is_first_time, aa.risk_score, aa.risk_category,
            o.name AS organizer_name, e.name AS event_name, aa.ticket_quantity,
            aa.is_flag as is_flagged
        FROM public.admin_alerts aa
        JOIN organizers o ON aa.organizer_id = o.id
        left JOIN events e ON aa.event_id = e.id
        WHERE 1=1
    """
    params = {}

    # Filter by alert type
    if alert_type and alert_type!=AlertType.AllCategories:
        query += " AND aa.alert_type = :alert_type"
        params["alert_type"] = alert_type

    # # Filter by risk category
    if risk_category and risk_category!=RiskCategory.AllCategories:
        query += " AND aa.risk_category = :risk_category"
        params["risk_category"] = risk_category.value

    # # Filter by duration (last N hours)
    if duration_hours:
        since = datetime.utcnow() - timedelta(hours=duration_hours)
        query += " AND aa.created_at >= :since"
        params["since"] = since
    # if popup==False:
    #     query += " AND aa.popup = False"
    # Pagination
    query += " ORDER BY aa.created_at DESC OFFSET :skip LIMIT :limit"
    params.update({"skip": skip, "limit": limit})

    alerts = db.execute(text(query), params).mappings().all()
    return [build_alert_response(alert) for alert in alerts]


def get_alert_details(alert_id: str, db: Session):
    result = db.execute(
        text("SELECT * FROM admin_alerts WHERE id = :alert_id"),
        {"alert_id": alert_id}
    ).mappings().first()

    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert_details = build_alert_response(result)
    detected_time = result["created_at"].strftime("%Y-%m-%d %H:%M:%S")

    response = {
        "alert_id": alert_details.id,
        "alert_title": alert_details.alert_title,
        "incident_description": alert_details.alert_description,
        "risk_score": alert_details.risk_score,
        "priority": alert_details.risk_category,
        "affected_entity": result.get("user_id"),
        "detected_time": detected_time
    }

    return {"alert_details": AlertDetails(**response)}


# ==============================
# Alert Resolution
# ==============================
def mark_alert_as_resolved(db: Session, alert_id: str):
    alert = db.execute(
        text("SELECT id, is_resolved FROM admin_alerts WHERE id = :alert_id"),
        {"alert_id": alert_id}
    ).mappings().first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert["is_resolved"]:
        return {"message": "Alert already resolved"}

    db.execute(
        text("""
            UPDATE admin_alerts
            SET is_resolved = true,
                updated_at = now()
            WHERE id = :alert_id
        """),
        {"alert_id": alert_id}
    )
    db.commit()

    return {"message": "Alert marked as resolved successfully", "alert_id": alert_id}

def mark_alert_as_flagged(db: Session, alert_id: str):
    alert = db.execute(
        text("SELECT id, is_flag FROM admin_alerts WHERE id = :alert_id"),
        {"alert_id": alert_id}
    ).mappings().first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    status = alert["is_flag"]
    status = not status

    db.execute(
        text("""
            UPDATE admin_alerts
            SET is_flag = :status,
                updated_at = now()
            WHERE id = :alert_id
        """),
        {"alert_id": alert_id, "status": status}
    )
    db.commit()
    if status == True:
        return {"message": "Alert flagged"}
    if status == False:
        return {"message": "Alert unflagged"}

def mark_alert_as_is_seen(db: Session, alert_id: str):
    alert = db.execute(
        text("SELECT id, is_seen FROM admin_alerts WHERE id = :alert_id"),
        {"alert_id": alert_id}
    ).mappings().first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert["is_seen"]:
        return {"message": "Alert already seen"}

    db.execute(
        text("""
            UPDATE admin_alerts
            SET is_seen = true,
                updated_at = now()
            WHERE id = :alert_id
        """),
        {"alert_id": alert_id}
    )
    db.commit()

    return {"message": "Alert marked as seen successfully"}

# ==============================
# Manual Testing Entry
# ==============================
if __name__ == "__main__":
    db = SessionLocal()
    # print(detect_combined_alerts(db))
    print(len(fetch_alerts(db, popup=False)))
