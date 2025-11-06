# Use an official Python base image
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /src/

# Copy dependency file first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt


COPY src/ .
# Copy environment variables file
COPY src/.env .env

# Copy the rest of the project files
#COPY . .

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
