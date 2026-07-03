# Imagen base con Python 3.11
FROM python:3.11-slim

# Metadatos
LABEL maintainer="TRAJANO Software"
LABEL description="ARGOS - Face Recognition Microservice with ArcFace"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema para OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements primero (para cache de Docker)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

# Pre-descargar modelo ArcFace para startup rápido
RUN python -c "from deepface import DeepFace; DeepFace.build_model('ArcFace')" || true

# Copiar código de la aplicación
COPY ARGOS/ ./ARGOS/
COPY runserver.py .

# Crear directorio para logs
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Exponer puerto interno (NO se publica, solo para Docker network)
EXPOSE 5000

# Healthcare check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)" || exit 1

# Usuario no-root para seguridad
RUN useradd -m -u 1000 argos && chown -R argos:argos /app
USER argos

# Comando de inicio con Gunicorn
CMD ["gunicorn", \
    "--bind", "0.0.0.0:5000", \
    "--workers", "2", \
    "--timeout", "120", \
    "--access-logfile", "/app/logs/access.log", \
    "--error-logfile", "/app/logs/error.log", \
    "--log-level", "info", \
    "ARGOS:app"]
