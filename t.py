import os
username = os.getenv("username")
password = os.getenv("password")
remote_host = os.getenv("remote_host")
port = os.getenv("port")
database_name = os.getenv("database_name")

print(f"postgresql://{username}:{password}@{remote_host}:{port}/{database_name}")
print("Y")