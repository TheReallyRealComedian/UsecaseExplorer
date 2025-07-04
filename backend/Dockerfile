# UsecaseExplorer/backend/Dockerfile
FROM python:3.11-alpine
WORKDIR /app

# Install netcat-openbsd for the entrypoint script
RUN apk add --no-cache netcat-openbsd

# This allows Python to find 'backend' and 'migrations' packages from /app
ENV PYTHONPATH /app

# Copy requirements first for better layer caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- CORRECTED COPY SECTION ---
# Copy all necessary application parts from the root build context (.)
COPY backend/ ./backend/
COPY migrations/ ./migrations/
COPY alembic.ini .

COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV FLASK_ENV=development
ENV PYTHONUNBUFFERED=1

# Proxy settings...
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""
ENV NO_PROXY=""

EXPOSE 5000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "1200", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "backend.app:create_app()"]
