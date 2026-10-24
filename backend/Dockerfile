FROM python:3.11-slim

WORKDIR /app

# Dépendances système nécessaires pour les libs PDF et ML
RUN apt-get -o Acquire::Retries=5 update && apt-get -o Acquire::Retries=5 install -y --fix-missing \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY config/requirements.txt .
RUN pip install --default-timeout=180 --retries 10 --no-cache-dir torch \
    --index-url https://download.pytorch.org/whl/cpu
RUN pip install --default-timeout=180 --retries 10 --no-cache-dir pyasn1==0.6.1
RUN pip install --default-timeout=180 --retries 10 --no-cache-dir -r requirements.txt

# Copier le code source complet (inclut les vectordb pré-construites)
# Les bases ChromaDB sont embarquées dans l'image — pas besoin de re-indexer
COPY . .

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8000"]
