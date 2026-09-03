FROM python:3.11-slim

# Installation de uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Définit le répertoire de travail
WORKDIR /app

# Copie les fichiers de configuration
COPY pyproject.toml .

# Crée le dossier data
RUN mkdir -p /data

# Installe les dépendances avec uv (sans build)
RUN uv pip install --system -r pyproject.toml

# Copie le code source après l'installation
COPY src/ ./src/
COPY scripts/ ./scripts/

# Définit les variables d'environnement
ENV PYTHONPATH=/app
ENV DATA_DIR=/data
ENV DB_PATH=/data/sorties.db

# Expose le port pour Streamlit
EXPOSE 8501

# Commande par défaut (scrape ponctuel de tous les clubs FFCAM configurés)
CMD ["uv", "run", "python", "scripts/run_scraper.py"]
