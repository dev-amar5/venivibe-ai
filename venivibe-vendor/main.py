import uvicorn
from fastapi import FastAPI
from routers.sales_prediction import router as sales_predicition_router
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title='user')
app.include_router(sales_predicition_router)
# app.include_router(test_router)
# app.include_router(event_tracking_router)

@app.get("/")
def home():
    return {"message": "Hello World"}

if __name__ == '__main__':
    print('starting')
    uvicorn.run(app, host='0.0.0.0', port=8000)
