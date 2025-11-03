from apscheduler.schedulers.background import BackgroundScheduler
from db import SessionLocal
from services.admin_notifications import (
    detect_combined_alerts,
    save_alert
)
import time
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def scheduled_jobs():
    with get_db() as db:
        try:
            logger.info("Running scheduled detection checks...")
            combined_alerts = detect_combined_alerts(db)

            if combined_alerts:
                print(combined_alerts)
                logger.info(f"{len(combined_alerts)} alerts detected!")
                for alert in combined_alerts:
                    save_alert(db=db, alert=alert)
                logger.info("Alerts saved successfully.")
            else:
                logger.info("No alerts detected.")

        except Exception as e:
            logger.error("Error during scheduled job:", exc_info=e)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_jobs, 'interval', minutes=5)
    scheduler.start()
    logger.info("Scheduler started... running every 5 minutes.")
    return scheduler

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_jobs, 'interval', minutes=5)  # runs every 5 minutes
    scheduler.start()

    logger.info("Scheduler started... running every 5 minutes.")
    try:
        while True:
            time.sleep(60)  # keep main thread alive
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")