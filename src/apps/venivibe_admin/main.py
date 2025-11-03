from fastapi import FastAPI
from src.apps.venivibe_admin.services.scheduler import start_scheduler
from src.apps.venivibe_admin.routers.admin_notifications import router as notifications_router
import logging

scheduler = start_scheduler()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title='user')
app.include_router(notifications_router)

@app.get("/")
def home():
    return {"message": "Hello World"}

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    logger.info("Scheduler stopped.")