FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend
COPY admin /app/admin
COPY bot /app/bot
COPY start.sh /app/start.sh

RUN chmod +x /app/start.sh

ENV PYTHONPATH=/app/backend:/app/bot

EXPOSE 8000

CMD ["/app/start.sh"]
