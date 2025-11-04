from fastapi import FastAPI
from src.apps.vendor.app import app as vendor_app
from src.apps.admin.app import app as admin_app

app = FastAPI(title="Venivibe Unified API")

# Mount each app under its own prefix
app.include_router(vendor_app.router, prefix="/vendor", tags=["Vendor"])
app.include_router(admin_app.router, prefix="/admin", tags=["Admin"])


@app.get("/")
def root():
    return {"message": "Venivibe API is running", "apps": ["vendor", "customer", "admin"]}
