#!/usr/bin/env python3
"""
CAF Crest Agenda Watcher
Scrape les sorties du CAF Crest et notifie des nouvelles sorties
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from src.database import SortiesDB

# plyer est optionnel (pas disponible dans Docker)
try:
    from plyer import notification
    HAS_NOTIFICATION = True
except ImportError:
    HAS_NOTIFICATION = False


class CAFWatcher:
    def __init__(self, data_dir: str = "/data"):
        self.url = "https://crest.ffcam.fr/agenda.html"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Utilise SQLite
        db_path = self.data_dir / "sorties.db"
        self.db = SortiesDB(str(db_path))
        
        # Garde aussi les fichiers JSON pour compatibilité
        self.all_sorties_file = self.data_dir / "all_sorties.json"
    
    def scrape_sorties(self) -> List[Dict]:
        """Scrape les sorties depuis le site du CAF"""
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            sorties = []
            
            # Trouve tous les éléments de sortie (nouvelle structure HTML)
            sortie_elements = soup.find_all('div', class_='row agenda_liste')
            
            for row in sortie_elements:
                try:
                    # Récupère toutes les colonnes
                    cols = row.find_all('div', recursive=False)
                    
                    if len(cols) < 6:
                        continue
                    
                    # Colonne 1: icône activité (on peut l'ignorer)
                    # Colonne 2: Date
                    date = cols[1].get_text(strip=True) if len(cols) > 1 else "N/A"
                    
                    # Colonne 3: Titre/Activité + URL
                    titre = "N/A"
                    url = ""
                    if len(cols) > 2:
                        titre_elem = cols[2].find('a')
                        if titre_elem:
                            titre = titre_elem.get_text(strip=True)
                            url = titre_elem.get('href', '')
                            if url and not url.startswith('http'):
                                url = f"https://crest.ffcam.fr{url}"
                        else:
                            titre = cols[2].get_text(strip=True)
                    
                    # Colonne 4: Lieu
                    lieu = cols[3].get_text(strip=True) if len(cols) > 3 else "N/A"
                    
                    # Colonne 5: Places + niveaux (images)
                    places = "N/A"
                    niveau_physique = 0
                    niveau_technique = 0
                    
                    if len(cols) > 4:
                        col5_text = cols[4].get_text(strip=True)
                        places = col5_text if col5_text else "N/A"
                        
                        # Extraction des niveaux depuis les URLs des images
                        imgs = cols[4].find_all('img')
                        for img in imgs:
                            src = img.get('src', '')
                            if 'Forme-physique' in src:
                                # Extrait le numéro (ex: Forme-physique02.png -> 2)
                                import re
                                match = re.search(r'Forme-physique(\d+)', src)
                                if match:
                                    niveau_physique = int(match.group(1))
                            elif 'Niveau' in src and 'Forme' not in src:
                                # Extrait le numéro (ex: Niveau02.png -> 2)
                                import re
                                match = re.search(r'Niveau(\d+)', src)
                                if match:
                                    niveau_technique = int(match.group(1))
                    
                    # Colonne 6: Contact
                    contact = cols[5].get_text(strip=True) if len(cols) > 5 else "N/A"
                    
                    # Détection de l'activité depuis l'icône (colonne 1)
                    activite = "Autre"
                    titre_lower = titre.lower()
                    
                    # D'abord vérifier SRN dans le titre (prioritaire)
                    if 'srn' in titre_lower or 'ski de randonnée nordique' in titre_lower or 'ski nordique' in titre_lower:
                        activite = "Ski de randonnée nordique"
                    elif len(cols) > 0:
                        img_icon = cols[0].find('img')
                        if img_icon:
                            src = img_icon.get('src', '')
                            if 'Raquette' in src:
                                activite = "Raquettes"
                            elif 'Randonnee' in src:
                                activite = "Randonnée"
                            elif 'Ski' in src or 'ski' in titre_lower:
                                activite = "Ski de randonnée"
                            elif 'Cascade' in titre or 'cascade' in titre_lower:
                                activite = "Cascade de glace"
                            elif 'Alpinisme' in src or 'alpi' in titre_lower:
                                activite = "Alpinisme"
                    
                    # Si pas d'icône, essaie de détecter depuis le titre
                    if activite == "Autre":
                        if 'raquette' in titre_lower:
                            activite = "Raquettes"
                        elif 'ski' in titre_lower:
                            activite = "Ski de randonnée"
                        elif 'cascade' in titre_lower:
                            activite = "Cascade de glace"
                        elif 'randonnée' in titre_lower or 'rando' in titre_lower:
                            activite = "Randonnée"
                        elif 'alpinisme' in titre_lower or 'alpi' in titre_lower:
                            activite = "Alpinisme"
                    
                    sortie_id = f"{date}_{titre}_{lieu}"
                    
                    sortie = {
                        'id': sortie_id,
                        'activite': activite,
                        'titre': titre,
                        'lieu': lieu,
                        'date': date,
                        'niveau_physique': niveau_physique,
                        'niveau_technique': niveau_technique,
                        'places': places,
                        'contact': contact,
                        'url': url,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    sorties.append(sortie)
                    
                except Exception as e:
                    print(f"Erreur lors du parsing d'une sortie: {e}")
                    continue
            
            return sorties
            
        except Exception as e:
            print(f"Erreur lors du scraping: {e}")
            return []
    
    def save_all_sorties(self, sorties: List[Dict]):
        """Sauvegarde toutes les sorties dans la base de données et JSON"""
        # 🔒 BACKUP automatique avant modification
        backup_path = self.db.create_backup()
        if backup_path:
            print(f"💾 Backup créé: {backup_path}")
        
        # Sauvegarde dans SQLite
        new_sorties = []
        for sortie in sorties:
            is_new = self.db.upsert_sortie(sortie)
            if is_new:
                new_sorties.append(sortie)
        
        # Garde aussi une copie JSON pour compatibilité
        with open(self.all_sorties_file, 'w', encoding='utf-8') as f:
            json.dump(sorties, f, indent=2, ensure_ascii=False)
        
        return new_sorties
    
    def send_notification(self, new_sorties: List[Dict]):
        """Envoie une notification pour les nouvelles sorties"""
        if not new_sorties:
            return
        
        count = len(new_sorties)
        title = f"🏔️ {count} nouvelle(s) sortie(s) CAF Crest!"
        
        # Message avec les 3 premières sorties
        messages = []
        for sortie in new_sorties[:3]:
            msg = f"• {sortie['activite']}: {sortie['titre']} ({sortie['date']})"
            messages.append(msg)
        
        if count > 3:
            messages.append(f"... et {count - 3} autre(s)")
        
        message = "\n".join(messages)
        
        # Notification desktop (si disponible)
        if HAS_NOTIFICATION:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name='CAF Watcher',
                    timeout=10
                )
                print(f"✅ Notification envoyée: {count} nouvelle(s) sortie(s)")
            except Exception as e:
                print(f"⚠️ Erreur notification desktop: {e}")
        
        # Log dans la console
        print(f"\n{'='*60}")
        print(title)
        print('='*60)
        for sortie in new_sorties:
            print(f"\n📍 {sortie['activite']}: {sortie['titre']}")
            print(f"   📅 Date: {sortie['date']}")
            print(f"   📍 Lieu: {sortie['lieu']}")
            print(f"   💪 Niveau physique: {sortie['niveau_physique']}")
            print(f"   🎯 Niveau technique: {sortie['niveau_technique']}")
            print(f"   👥 {sortie['places']}")
            print(f"   📞 Contact: {sortie['contact']}")
        print(f"\n{'='*60}\n")
    
    def check_for_updates(self):
        """Vérifie les nouvelles sorties"""
        print(f"🔍 Vérification des sorties CAF Crest... [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        
        # Scrape les sorties actuelles
        current_sorties = self.scrape_sorties()
        
        if not current_sorties:
            print("⚠️ Aucune sortie récupérée")
            return
        
        print(f"📊 {len(current_sorties)} sorties trouvées au total")
        
        # Sauvegarde toutes les sorties et récupère les nouvelles
        new_sorties = self.save_all_sorties(current_sorties)
        
        if new_sorties:
            print(f"🆕 {len(new_sorties)} nouvelle(s) sortie(s)")
            self.send_notification(new_sorties)
        else:
            print("✅ Aucune nouvelle sortie")
    
    def run_continuous(self, interval_hours: int = 12):
        """Lance le watcher en continu"""
        print(f"🚀 Démarrage du watcher (vérification toutes les {interval_hours}h)")
        
        while True:
            try:
                self.check_for_updates()
                interval_seconds = interval_hours * 3600
                print(f"⏳ Prochaine vérification dans {interval_hours}h...")
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                print("\n👋 Arrêt du watcher")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
                print("⏳ Nouvelle tentative dans 5 minutes...")
                time.sleep(300)


def main():
    # Récupère l'intervalle depuis les variables d'environnement
    interval = int(os.getenv('CHECK_INTERVAL_HOURS', '12'))
    
    watcher = CAFWatcher()
    
    # Si on veut juste vérifier une fois
    if os.getenv('RUN_ONCE', 'false').lower() == 'true':
        watcher.check_for_updates()
    else:
        watcher.run_continuous(interval_hours=interval)


if __name__ == "__main__":
    main()

