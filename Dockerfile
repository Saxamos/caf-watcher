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

# Définit les variables d'environnement
ENV CHECK_INTERVAL_HOURS=12
ENV RUN_ONCE=false
ENV PYTHONPATH=/app

# Commande par défaut
CMD ["uv", "run", "python", "-c", "from src.scraper import CAFWatcher; import os; CAFWatcher('/data').run_continuous(int(os.getenv('CHECK_INTERVAL_HOURS', '12'))) if os.getenv('RUN_ONCE', 'false').lower() != 'true' else CAFWatcher('/data').check_for_updates()"]
