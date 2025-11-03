from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class AdminAlert(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    alert_type: Optional[str] = None
    user_id: Optional[UUID] = None
    event_id: Optional[UUID] = None
    organizer_id: Optional[UUID] = None
    refund_count: Optional[float] = None
    login_fail_count: Optional[float] = None
    ticket_price: Optional[float] = None
    ticket_quantity: Optional[int] = None
    is_first_time: Optional[bool] = None
    risk_score: Optional[float] = None
    risk_category: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RiskCategory(str, Enum):
    Low = "Low"
    Moderate = "Moderate"
    High = "High"
    AllCategories = "AllCategories"


class AlertType(str, Enum):
    LoginFail = "Multiple Failed Logins"
    MassRefund = "Mass Refund"
    SuspiciousBulkPurchase = "Suspicious Bulk Purchase"
    HighValueEvent = "New High-Value Event"
    AllCategories = "All Categories"


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
    ticket_quantity: Optional[int] = None
    is_first_time: Optional[bool] = None
    risk_score: Optional[float] = None
    risk_category: Optional[str] = None
    is_flagged: Optional[bool] = None

class AlertDetails(BaseModel):
    alert_id: UUID
    alert_title: str
    incident_description: Optional[str] = None
    risk_score: float
    priority: str
    affected_entity: Optional[UUID] = None
    detected_time: datetime
    user_access_logs: Optional[list] = None
    customer_complaints: Optional[list] = None
    related_transactions: Optional[list] = None