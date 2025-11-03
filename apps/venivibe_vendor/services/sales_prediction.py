
from sqlalchemy import text
from sqlalchemy.orm import Session
from db import SessionLocal

from statsmodels.tsa.holtwinters import SimpleExpSmoothing
from sklearn.linear_model import LinearRegression
from fastapi import HTTPException

from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
from sklearn.linear_model import LinearRegression


def sales_predict(event_id: str, db: Session, n_future: int = 6, w: float = 0) -> Dict[str, Any]:
    # Fetch sales data
    result = db.execute(text("""
        SELECT o.created_at, pt.quantity, pt.quantity * tt.price AS sales
        FROM orders o
        JOIN purchased_tickets pt ON o.id = pt.order_id
        JOIN ticket_types tt ON o.event_id = tt.event_id
        WHERE o.event_id = :event_id
        ORDER BY o.created_at
    """), {"event_id": event_id}).fetchall()

    df = pd.DataFrame(result, columns=["created_at", "quantity", "price"])

    if df.empty:
        return {"historical": [], "predicted": []}

    # Historical sales
    sales = np.array(df["price"]).astype(int)
    time = np.arange(len(sales)).reshape(-1, 1)

    # Linear Regression Forecast
    lr = LinearRegression().fit(time, sales)
    time_future = np.arange(len(sales), len(sales) + n_future).reshape(-1, 1)
    lr_forecast_future = lr.predict(time_future)

    # Simple Exponential Smoothing Forecast
    ses_model = SimpleExpSmoothing(sales).fit(smoothing_level=0.5, optimized=False)
    ses_forecast_future = ses_model.forecast(n_future)

    # Combine (Hybrid Forecast)
    final_forecast_future = (1 - w) * ses_forecast_future + w * lr_forecast_future

    # Build date ranges
    last_date = pd.to_datetime(df["created_at"].iloc[-1])
    future_dates = [last_date + timedelta(days=i + 1) for i in range(n_future)]

    # Format data for chart
    historical_data = [
        {"date": str(d.date()), "sales": int(s)} for d, s in zip(df["created_at"], sales)
    ]
    predicted_data = [
        {"date": str(d.date()), "forecast": float(f)} for d, f in zip(future_dates, final_forecast_future)
    ]

    return {"historical": historical_data, "predicted": predicted_data}

from sqlalchemy import text
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
from datetime import timedelta


def hybrid_forecast_api(event_id, db, n_future=6, w=0.5):
    result = db.execute(text("""
        SELECT o.created_at, pt.quantity, pt.quantity * tt.price AS sales
        FROM orders o
        JOIN purchased_tickets pt ON o.id = pt.order_id
        JOIN ticket_types tt ON o.event_id = tt.event_id
        WHERE o.event_id = :event_id
        ORDER BY o.created_at
    """), {"event_id": event_id}).fetchall()

    df = pd.DataFrame(result, columns=['created_at', 'quantity', 'sales'])
    # df['created_at'] = pd.to_datetime(df['created_at']).dt.date
    df['created_at'] = pd.to_datetime(df['created_at'])
    # Group by day
    daily_sales = df.groupby('created_at')['sales'].sum().reset_index()
    daily_sales['created_at'] = pd.to_datetime(daily_sales['created_at'])
    daily_sales['days_since_first'] = (daily_sales['created_at'] - daily_sales['created_at'].min()).dt.days
    daily_sales['week_number'] = (daily_sales['days_since_first'] // 7) + 1  # week 1, 2, 3...
    # daily_sales['week_number'] = daily_sales['created_at'].dt.isocalendar().week
    daily_sales['year'] = daily_sales['created_at'].dt.year
    weekly_sales_comparison = daily_sales.groupby('week_number', as_index=False)['sales'].sum()
    weekly_sales_comparison['previous_week_sales'] = weekly_sales_comparison['sales'].shift(1)
    weekly_sales_comparison['previous_week_sales'] = weekly_sales_comparison['previous_week_sales'].astype(float)


    weekly_sales_comparison['previous_week_sales'] = weekly_sales_comparison['previous_week_sales'].apply(
        lambda x: 0 if pd.isna(x) else float(x)
    )
    weekly_sales_comparison['sales'] = weekly_sales_comparison['sales'].astype(float)

    # Check BEFORE modeling
    if len(daily_sales) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough data to forecast. Found {len(daily_sales)} records, minimum 5 required."
        )

    # Prepare data
    sales = daily_sales['sales'].astype(float).values
    time = np.arange(len(sales)).reshape(-1, 1)

    # Linear Regression
    lr = LinearRegression().fit(time, sales)

    # Simple Exponential Smoothing
    ses_model = SimpleExpSmoothing(sales).fit(smoothing_level=0.5, optimized=False)

    # Forecast
    future_dates = [daily_sales['created_at'].max() + timedelta(days=i+1) for i in range(n_future)]
    lr_forecast = [lr.predict([[len(sales)+i]])[0] for i in range(n_future)]
    ses_forecast = ses_model.forecast(n_future)
    final_forecast = [(1-w)*ses + w*lr for ses, lr in zip(ses_forecast, lr_forecast)]

    # Format historical
    historical = [
        {
            "date": str(row['created_at']),
            "day_of_week": pd.to_datetime(row['created_at']).strftime("%A"),
            "sales": float(row['sales'])
        }
        for _, row in daily_sales.iterrows()
    ]

    # Format forecast
    forecast = [
        {
            "date": str(date),
            "day_of_week": pd.to_datetime(date).strftime("%A"),
            "forecast_sales": int(value)
        }
        for date, value in zip(future_dates, final_forecast)
    ]
    # return weekly_sales_comparison

    sales_comparison = weekly_sales_comparison.to_dict(orient='records')
    # return sales_comparison

    return {"sales_prediction":{
        "historical": historical,
        "forecast": forecast,
        "forecast_horizon_days": n_future
    },
    "sales_comparison": sales_comparison}

# len(hybrid_forecast_api(event_id=event_id, db=db, n_future=10000, w=0.6)['forecast'])

if __name__ == "__main__":
    db = SessionLocal()
    event_id = 'fb8156a0-4432-46f7-a733-27c0ba3ae2d4'
    # print(sales_predict(event_id=event_id,db=db))
    print(hybrid_forecast_api(event_id=event_id,db=db))

