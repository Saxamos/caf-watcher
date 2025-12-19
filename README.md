# 🏔️ CAF Crest Watcher

Application de surveillance des sorties du CAF Crest avec interface web moderne.

## 📁 Structure du projet

```
caf-watcher/
├── src/                    # Code source
│   ├── database.py        # Gestion SQLite
│   ├── scraper.py         # Scraper web
│   └── app.py            # Application Streamlit
├── scripts/               # Scripts utilitaires
│   └── run_scraper.py    # Lance le scraper manuellement
├── data/                  # Données (créé automatiquement)
│   └── sorties.db        # Base de données SQLite
├── pyproject.toml        # Configuration uv & dépendances
├── Dockerfile            # Image Docker
├── docker-compose.yml    # Configuration Docker
└── Makefile              # Commandes rapides
```

## 🚀 Démarrage rapide

### Prérequis

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Gestionnaire de paquets Python ultra-rapide

Installation de uv :
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

```bash
# Clone le projet
git clone <repo-url>
cd caf-watcher

# Installe les dépendances
make install
```

## 💻 Utilisation

### Mode Docker (recommandé)

Lance l'interface web Streamlit en arrière-plan :

```bash
# Build et lance l'app
make docker-build
make docker-up

# L'app sera accessible sur http://localhost:8501

# Voir les logs
make docker-logs

# Arrêter
make docker-down
```

### Interface Web Streamlit

L'application web permet de :
- 🔄 **Scraper à la demande** avec le bouton "Rafraîchir"
- ✅ Liste des sorties avec checkboxes pour marquer comme vu
- 🔍 Filtres par activité, niveau, statut
- 📊 Statistiques en temps réel
- 🎯 Groupement par activité
- 📋 Vue détaillée de chaque sortie
- 🔗 Liens directs vers les sorties CAF

**Note :** Le scraping est maintenant **à la demande uniquement** via le bouton dans l'interface. Plus de scraping automatique en arrière-plan.

## 📝 Commandes disponibles

```bash
make help              # Affiche toutes les commandes
make clean             # Nettoie les fichiers temporaires
make docker-build      # Build l'image Docker
make docker-up         # Lance le container
make docker-down       # Arrête le container
make docker-logs       # Voir les logs
make docker-scrape     # Scrape une fois avec Docker
```

## 🗄️ Base de données

SQLite est utilisé pour stocker les sorties :
- **Table `sorties`** : stocke toutes les sorties avec leur statut (vu/non vu)
- **Indexes** : optimisés pour les requêtes fréquentes
- **Fichier** : `data/sorties.db`

## 🔧 Configuration

Variables d'environnement (Docker) :
- `DB_PATH` : Chemin vers la base de données SQLite (défaut: `/data/sorties.db` en Docker, `data/sorties.db` en local)
- `DATA_DIR` : Répertoire des données pour le scraper (défaut: `/data` en Docker, `data` en local)

## 📦 Dépendances

- **requests** : Client HTTP
- **beautifulsoup4** : Parsing HTML
- **streamlit** : Interface web
- **lxml** : Parser XML/HTML rapide

Géré par `uv` via `pyproject.toml`

## 🐛 Développement

```bash
# Active l'environnement virtuel
source .venv/bin/activate

# Lance l'app en mode dev
uv run streamlit run src/app.py --server.port 8501

# Nettoie tout
make clean
```

## 📄 License

MIT
