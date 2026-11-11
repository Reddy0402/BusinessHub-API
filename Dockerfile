FROM python:3.12-slim

# Don't write .pyc files, and show logs immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Install dependencies first so Docker can cache this layer between builds
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application (includes app/version.txt when the deploy pipeline writes it)
COPY app ./app

# Run as a normal user instead of root
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# 0.0.0.0 accepts outside connections; Railway sets PORT, locally it defaults to 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
