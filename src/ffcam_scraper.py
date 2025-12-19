#!/usr/bin/env python3
"""
FFCAM Sorties Scraper
Scrape les sorties depuis sorties.ffcam.fr (nécessite authentification)
"""

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup


class FFCAMScraper:
    def __init__(self, data_dir: str = "/data"):
        self.base_url = "https://sorties.ffcam.fr"
        self.sorties_url = f"{self.base_url}/sortie/liste"
        self.data_dir = Path(data_dir)
        self.cookies_file = self.data_dir / "ffcam_cookies.pkl"
        self.session = requests.Session()
        self._load_cookies()
    
    def _load_cookies(self):
        """Charge les cookies depuis le fichier"""
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                    self.session.cookies.update(cookies)
                print(f"✅ Cookies FFCAM chargés depuis {self.cookies_file}")
            except Exception as e:
                print(f"⚠️ Erreur lors du chargement des cookies: {e}")
    
    def save_cookies(self, cookies_dict: Dict[str, str]):
        """Sauvegarde les cookies manuellement fournis"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Crée un jar de cookies
            for name, value in cookies_dict.items():
                self.session.cookies.set(name, value, domain='.ffcam.fr')
            
            # Sauvegarde
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(self.session.cookies, f)
            
            print(f"✅ Cookies FFCAM sauvegardés dans {self.cookies_file}")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde des cookies: {e}")
            return False
    
    def test_authentication(self) -> bool:
        """Teste si l'authentification fonctionne"""
        try:
            response = self.session.get(self.sorties_url, timeout=30)
            
            # Si on est redirigé vers la page de login, on n'est pas authentifié
            if 'login' in response.url or response.status_code == 401:
                print("❌ Non authentifié - cookies invalides ou expirés")
                return False
            
            # Vérifie qu'on a bien accès au contenu
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Cherche un élément qui n'apparaît que quand on est connecté
                if soup.find('a', href='/logout') or soup.find('div', class_='user-menu'):
                    print("✅ Authentifié avec succès!")
                    return True
            
            print(f"⚠️ Status ambigu: {response.status_code}")
            return False
            
        except Exception as e:
            print(f"❌ Erreur lors du test d'authentification: {e}")
            return False
    
    def scrape_sorties(self, max_pages: int = 5) -> List[Dict]:
        """Scrape les sorties depuis sorties.ffcam.fr"""
        if not self.test_authentication():
            print("❌ Impossible de scraper sans authentification valide")
            return []
        
        all_sorties = []
        
        try:
            for page in range(1, max_pages + 1):
                print(f"📄 Scraping page {page}/{max_pages}...")
                
                params = {'page': page}
                response = self.session.get(self.sorties_url, params=params, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Trouve les sorties (structure à adapter selon le HTML réel)
                sortie_elements = soup.find_all('div', class_='sortie-item')  # À ajuster
                
                if not sortie_elements:
                    print(f"⚠️ Aucune sortie trouvée sur la page {page}")
                    break
                
                for elem in sortie_elements:
                    try:
                        sortie = self._parse_sortie(elem)
                        if sortie:
                            all_sorties.append(sortie)
                    except Exception as e:
                        print(f"⚠️ Erreur parsing sortie: {e}")
                        continue
                
                print(f"✅ {len(sortie_elements)} sorties trouvées sur la page {page}")
            
            print(f"📊 Total: {len(all_sorties)} sorties FFCAM récupérées")
            return all_sorties
            
        except Exception as e:
            print(f"❌ Erreur lors du scraping FFCAM: {e}")
            return []
    
    def _parse_sortie(self, elem) -> Optional[Dict]:
        """Parse un élément de sortie (à adapter selon le HTML réel)"""
        try:
            # IMPORTANT: Cette structure est à adapter une fois qu'on voit le HTML réel
            # Pour l'instant, c'est un template
            
            titre_elem = elem.find('h3') or elem.find('a', class_='sortie-titre')
            titre = titre_elem.get_text(strip=True) if titre_elem else "N/A"
            
            # URL
            url = ""
            if titre_elem and titre_elem.name == 'a':
                url = titre_elem.get('href', '')
                if url and not url.startswith('http'):
                    url = f"{self.base_url}{url}"
            
            # Date
            date_elem = elem.find('span', class_='date') or elem.find('time')
            date = date_elem.get_text(strip=True) if date_elem else "N/A"
            
            # Lieu
            lieu_elem = elem.find('span', class_='lieu')
            lieu = lieu_elem.get_text(strip=True) if lieu_elem else "N/A"
            
            # Activité
            activite_elem = elem.find('span', class_='activite')
            activite = activite_elem.get_text(strip=True) if activite_elem else "Autre"
            
            # Contact/Organisateur
            contact_elem = elem.find('span', class_='organisateur')
            contact = contact_elem.get_text(strip=True) if contact_elem else "N/A"
            
            sortie_id = f"ffcam_{date}_{titre}_{lieu}"
            
            return {
                'id': sortie_id,
                'source': 'FFCAM',
                'activite': activite,
                'titre': titre,
                'lieu': lieu,
                'date': date,
                'niveau_physique': 0,  # À extraire si disponible
                'niveau_technique': 0,  # À extraire si disponible
                'places': "N/A",
                'contact': contact,
                'url': url,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"⚠️ Erreur parsing sortie: {e}")
            return None
    
    def get_page_html(self, save_to_file: bool = True) -> str:
        """Récupère le HTML de la page pour analyse (debug)"""
        try:
            response = self.session.get(self.sorties_url, timeout=30)
            response.raise_for_status()
            
            if save_to_file:
                debug_file = self.data_dir / "ffcam_page.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"💾 HTML sauvegardé dans {debug_file}")
            
            return response.text
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return ""


def main():
    """Test du scraper"""
    scraper = FFCAMScraper(data_dir="data")
    
    # Test authentification
    if scraper.test_authentication():
        # Récupère le HTML pour analyse
        scraper.get_page_html()
        
        # Essaie de scraper
        sorties = scraper.scrape_sorties(max_pages=2)
        print(f"\n📊 Résultat: {len(sorties)} sorties")
        
        if sorties:
            print("\n🎯 Première sortie:")
            print(json.dumps(sorties[0], indent=2, ensure_ascii=False))
    else:
        print("\n⚠️ Utilise le script scripts/import_cookies.py pour configurer l'authentification")


if __name__ == "__main__":
    main()

