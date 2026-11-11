# Production-oriented Dockerfile for BusinessHub API
FROM python:3.12-slim

WORKDIR /app

# Install production dependencies only
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Listen on all interfaces; PORT defaults to 8000
ENV PORT=8000

# Run the application with uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
