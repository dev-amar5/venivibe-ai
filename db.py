from sqlalchemy import create_engine,text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# from credentials import *
import os
from dotenv import load_dotenv
load_dotenv()

username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")
remote_host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
database_name = os.getenv("DB_NAME")

# PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# root = "/home/rahul/PycharmProjects/venivibe"
root = os.path.dirname(os.path.abspath(__file__))

# db_path = os.path.join(root, "zali.db")  # full path to DB file
# SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://rahul:123@localhost:5432/db1"
SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{password}@{remote_host}:{port}/{database_name}"


engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency for FastAPI
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == '__main__':
    db = SessionLocal()

    # run a query
    result = db.execute(text("SELECT * FROM chats;")).fetchall()

    # print results
    for row in result:
        print(row)

    db.close()
