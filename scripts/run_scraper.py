#!/usr/bin/env python3
"""Script pour lancer le scraper manuellement (tous les clubs FFCAM configurés)"""

import sys
import os
from pathlib import Path

# Ajoute le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import SortiesDB
from src.ffcam_scraper import FFCAMScraper
from src.ffcam_formations_scraper import FFCAMFormationsScraper
from src.clubs import get_clubs

if __name__ == "__main__":
    # Utilise /data en Docker, data en local
    data_dir = os.getenv('DATA_DIR', 'data')
    db_path = os.getenv('DB_PATH', os.path.join(data_dir, 'sorties.db'))
    db = SortiesDB(db_path)

    total_new = 0
    for club in get_clubs():
        scraper = FFCAMScraper(club_id=club["club_id"], club_label=club["label"], source_key=club["key"])
        sorties = scraper.scrape_sorties()
        print(f"📡 {club['label']}: {len(sorties)} sorties récupérées")
        for sortie in sorties:
            if db.upsert_sortie(sortie):
                total_new += 1

    formations = FFCAMFormationsScraper().scrape_formations()
    print(f"📚 FFCAM Formations: {len(formations)} formations récupérées")
    for sortie in formations:
        if db.upsert_sortie(sortie):
            total_new += 1

    print(f"🆕 {total_new} nouvelle(s) sortie(s) au total")
