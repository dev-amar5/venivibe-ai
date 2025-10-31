from fastapi import APIRouter, Depends, Query
from db import get_db_session
from services.sales_prediction import *

router = APIRouter(prefix="/sales_prediction", tags=["sales_prediction"])

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from db import get_db_session

# app = FastAPI()
# router = APIRouter(prefix="/sales_estimates", tags=["eventtracking"])


@router.get("/sales_forecast/{event_id}")
def get_sales_forecast(event_id: str, n_future: int = 6, db: Session = Depends(get_db_session)):
    return hybrid_forecast_api(event_id, db, n_future=n_future, w=0.5)

