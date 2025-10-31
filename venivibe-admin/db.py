from sqlalchemy import create_engine,text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# from credentials import *
import os
from dotenv import load_dotenv
load_dotenv()

username = os.getenv("username")
password = os.getenv("password")
remote_host = os.getenv("remote_host")
port = os.getenv("port")
database_name = os.getenv("database_name")

# PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
root = "/home/rahul/PycharmProjects/venivibe"
db_path = os.path.join(root, "zali.db")  # full path to DB file
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
