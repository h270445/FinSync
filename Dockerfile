# The FinSync API (FastAPI on Uvicorn). Used by compose.yaml; see docs/guides/getting-started.md.
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY finsync ./finsync
EXPOSE 8080
# The database comes from FINSYNC_DATABASE_URL; the schema is created or upgraded on start (Alembic).
CMD ["sh", "-c", "python -m finsync.api --host 0.0.0.0 --port 8080 --db \"$FINSYNC_DATABASE_URL\""]
