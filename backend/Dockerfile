# UsecaseExplorer/backend/Dockerfile
FROM python:3.11-alpine
WORKDIR /app

# Copy requirements.txt from the build context (which is ./backend/)
# to the current WORKDIR (/app) in the container.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all contents of the build context (which is the ./backend/ directory)
# into a subdirectory named 'backend' within the WORKDIR (/app/backend/) inside the container.
COPY . /app/backend/

# Set PYTHONPATH to include /app/backend so Python can find your 'backend' package
# where your Flask app ('backend:create_app()') resides.
ENV PYTHONPATH=/app/backend

EXPOSE 5000

# Command to run the Gunicorn server.
# 'backend:create_app()' refers to the create_app() function within the 'backend' Python package.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "backend:create_app()"]
