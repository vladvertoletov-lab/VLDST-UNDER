FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend
COPY admin /app/admin
COPY bot /app/bot
COPY start.py /app/start.py

ENV PYTHONPATH=/app/backend:/app

CMD ["python", "/app/start.py"]
