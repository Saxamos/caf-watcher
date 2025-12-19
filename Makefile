.PHONY: help clean docker-build docker-up docker-down docker-logs docker-scrape

help: ## Affiche l'aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

clean: ## Nettoie les fichiers temporaires
	rm -rf data/*.json
	rm -rf .venv __pycache__ src/__pycache__ scripts/__pycache__
	rm -rf .pytest_cache .coverage htmlcov

docker-build: ## Construit l'image Docker
	docker-compose build

docker-up: ## Lance le container Docker en arrière-plan
	docker-compose up -d

docker-down: ## Arrête le container Docker
	docker-compose down

docker-logs: ## Affiche les logs du container
	docker-compose logs -f

docker-scrape: ## Lance le scraper une fois
	docker-compose run --rm -e DATA_DIR=/data app uv run python scripts/run_scraper.py
