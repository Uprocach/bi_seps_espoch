FROM python:3.12-slim AS backend

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Copiar requerimientos e instalar dependencias Python
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copiar código del backend y configuraciones requeridas
COPY backend ./backend
COPY config ./config
COPY contracts ./contracts

# Puerto interno expuesto
EXPOSE 8000

# 4 workers Uvicorn con DuckDB embebido en memoria por worker
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
