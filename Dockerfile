FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend
COPY admin /app/admin
COPY bot /app/bot
COPY render_start.sh /app/render_start.sh

RUN chmod +x /app/render_start.sh

ENV PYTHONPATH=/app/backend:/app

CMD ["/app/render_start.sh"]
