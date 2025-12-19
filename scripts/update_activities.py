#!/usr/bin/env python3
"""
Script pour mettre à jour les activités des sorties existantes
sans perdre les statuts "vu"
"""
import sys
sys.path.insert(0, '/app')

from src.database import SortiesDB
from src.scraper import CAFWatcher

def update_activities():
    """Met à jour les activités en gardant les statuts vus"""
    print("🔄 Mise à jour des activités sans perdre les statuts vus...\n")
    
    # Initialise le watcher et la DB
    watcher = CAFWatcher('/data')
    db = watcher.db
    
    # Récupère toutes les sorties existantes avec leurs statuts
    existing_sorties = db.get_all_sorties()
    seen_ids = {s['id']: s['vu'] for s in existing_sorties}
    
    print(f"📊 {len(existing_sorties)} sorties en DB")
    print(f"✅ {sum(1 for v in seen_ids.values() if v)} sorties marquées comme vues\n")
    
    # Scrape les nouvelles données
    print("📡 Scraping des données fraîches...")
    fresh_sorties = watcher.scrape_sorties()
    print(f"📥 {len(fresh_sorties)} sorties récupérées\n")
    
    # Met à jour les sorties en gardant les statuts vus
    updated_count = 0
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

