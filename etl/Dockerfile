# Python ETL
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 -r requirements.txt

# Copy ETL scripts
COPY . .

# Default command (can be overridden in docker-compose)
CMD ["python", "schedulers/cron_jobs.py"]
