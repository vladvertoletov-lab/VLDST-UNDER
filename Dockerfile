FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app/backend
COPY frontend /app/frontend
COPY admin /app/admin
COPY bot /app/bot
ENV PYTHONPATH=/app/backend:/app/bot
CMD ["sh","-c","PYTHONPATH=/app/backend alembic -c /app/backend/alembic.ini upgrade head && PYTHONPATH=/app/backend python -m app.seed && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
