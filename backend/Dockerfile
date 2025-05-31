# UsecaseExplorer/backend/Dockerfile
FROM python:3.11-alpine
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/backend/

ENV PYTHONPATH=/app/backend

# This sets the Flask environment to development
ENV FLASK_ENV=development
# This ensures Python output is unbuffered for immediate output from Python prints
ENV PYTHONUNBUFFERED=1

# Ensure no proxy environment variables interfere with HTTPX clients
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""
ENV ALL_PROXY=""
ENV NO_PROXY=""

EXPOSE 5000

# Use the Exec Form. Ensure 'backend:create_app()' is the LAST element.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "1200", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "backend:create_app()"]