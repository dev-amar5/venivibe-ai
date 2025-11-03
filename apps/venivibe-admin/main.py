from fastapi import FastAPI
from services.scheduler import start_scheduler
# from apis.auth import router as auth_router, get_current_user
# from apis.users import router as users_router
# from apis.test import router as test_router
# from apis.tasks import router as tasks_router
from routers.admin_notifications import router as notifications_router
import logging

scheduler = start_scheduler()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title='user')
app.include_router(notifications_router)
# app.include_router(test_router)
# app.include_router(event_tracking_router)

@app.get("/")
def home():
    return {"message": "Hello World"}

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    logger.info("Scheduler stopped.")