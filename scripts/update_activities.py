#!/usr/bin/env python3
"""
Script pour mettre à jour les sorties existantes (tous les clubs FFCAM)
sans perdre les statuts "vu"
"""
import sys
sys.path.insert(0, '/app')

from src.database import SortiesDB
from src.ffcam_scraper import FFCAMScraper
from src.clubs import get_clubs


def update_activities():
    """Met à jour les sorties en gardant les statuts vus"""
    print("🔄 Mise à jour des sorties sans perdre les statuts vus...\n")

    db = SortiesDB('/data/sorties.db')

    # Récupère toutes les sorties existantes avec leurs statuts
    existing_sorties = db.get_all_sorties()
    seen_ids = {s['id']: s['vu'] for s in existing_sorties}

    print(f"📊 {len(existing_sorties)} sorties en DB")
    print(f"✅ {sum(1 for v in seen_ids.values() if v)} sorties marquées comme vues\n")

    updated_count = 0
    for club in get_clubs():
        scraper = FFCAMScraper(club_id=club["club_id"], club_label=club["label"], source_key=club["key"])
        print(f"📡 Scraping {club['label']}...")
        fresh_sorties = scraper.scrape_sorties()
        print(f"📥 {len(fresh_sorties)} sorties récupérées\n")

        for sortie in fresh_sorties:
            # Garde le statut vu si la sortie existait déjà
            if sortie['id'] in seen_ids:
                sortie['vu'] = seen_ids[sortie['id']]

            # Upsert (insert or update)
            db.upsert_sortie(sortie, force_update=True)
            updated_count += 1

    print(f"✅ {updated_count} sorties mises à jour")
    print(f"✅ Statuts 'vu' préservés\n")


if __name__ == "__main__":
    update_activities()
