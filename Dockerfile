# Dockerfile para la app Django
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del sistema (mínimas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Copiar el código
COPY . /app

EXPOSE 8000

# Comando por defecto: migrar y arrancar server de desarrollo
CMD ["bash", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]