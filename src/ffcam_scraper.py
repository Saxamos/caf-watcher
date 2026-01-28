#!/usr/bin/env python3
"""
FFCAM Sorties Scraper
Récupère les sorties depuis sorties.ffcam.fr via cookies de session (comme le navigateur).
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup


class FFCAMScraper:
    def __init__(self, data_dir: str = "/data"):
        self.base_url = "https://sorties.ffcam.fr"
        self.api_url = "https://api.sorties.ffcam.fr/for-club/outing"
        self.page_url = f"{self.base_url}/outing"
        self.data_dir = Path(data_dir)
        self.cookies_file = self.data_dir / "ffcam_cookies.txt"
        self.cookie_header: Optional[str] = None
        self._load_cookies()

    def _load_cookies(self):
        """Charge les cookies depuis le fichier (valeur du header Cookie)."""
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, "r") as f:
                    self.cookie_header = f.read().strip()
                if self.cookie_header:
                    print("✅ Cookies FFCAM chargés")
            except Exception as e:
                print(f"⚠️ Erreur chargement cookies: {e}")

    def save_cookies(self, cookie_string: str) -> bool:
        """Sauvegarde la chaîne Cookie (copiée depuis DevTools > Network > Request Headers > Cookie)."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cookies_file, "w") as f:
                f.write(cookie_string.strip())
            self.cookie_header = cookie_string.strip()
            print("✅ Cookies FFCAM sauvegardés")
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde cookies: {e}")
            return False

    def has_auth(self) -> bool:
        """Indique si une auth (cookies) est configurée."""
        return bool(self.cookie_header)

    def _session_headers(self) -> Dict[str, str]:
        """Headers pour les requêtes avec la session navigateur."""
        h = {
            "Accept": "text/html,application/xhtml+xml,application/json",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        if self.cookie_header:
            h["Cookie"] = self.cookie_header
        return h

    def scrape_sorties(self, max_pages: int = 5) -> List[Dict]:
        """
        Récupère les sorties : d'abord via l'API avec les cookies,
        sinon en parsant la page HTML (données embarquées).
        """
        if not self.cookie_header:
            print("❌ Aucun cookie configuré. Colle le header Cookie depuis DevTools (sur sorties.ffcam.fr).")
            return []

        # 1) Tenter l'API avec les cookies
        sorties = self._scrape_via_api()
        if sorties:
            return sorties

        # 2) Fallback : récupérer la page HTML et extraire les données embarquées
        sorties = self._scrape_via_page_html()
        return sorties

    def _scrape_via_api(self) -> List[Dict]:
        """Appel API avec les cookies de session."""
        try:
            params = {
                "sort": '[["startDate",1]]',
                "q": json.dumps({
                    "fetchType": "published",
                    "status": {"in": ["published", "validated"]},
                    "startDate": {"gte": datetime.now().isoformat()},
                }),
            }
            headers = {**self._session_headers(), "Accept": "application/json"}
            r = requests.get(
                self.api_url,
                headers=headers,
                params=params,
                timeout=30,
            )
            if r.status_code != 200:
                return []
            data = r.json()
            if isinstance(data, list):
                return self._parse_sorties(data)
            return []
        except Exception as e:
            print(f"⚠️ API avec cookies: {e}")
            return []

    def _scrape_via_page_html(self) -> List[Dict]:
        """Charge la page /outing avec les cookies et extrait les sorties du HTML (JSON embarqué)."""
        try:
            r = requests.get(
                self.page_url,
                headers=self._session_headers(),
                timeout=30,
            )
            r.raise_for_status()
            html = r.text

            # Redirection vers login = pas de cookies valides
            if "login" in r.url.lower() or "connexion" in html.lower():
                print("❌ Session expirée ou cookies invalides (page login détectée).")
                return []

            data = self._extract_json_from_page(html)
            if data:
                return self._parse_sorties(data)
            return []
        except Exception as e:
            print(f"❌ Récupération page HTML: {e}")
            return []

    def _extract_json_from_page(self, html: str) -> Optional[List[Dict]]:
        """Cherche dans le HTML des blocs JSON contenant des sorties (outings)."""
        soup = BeautifulSoup(html, "html.parser")

        # Script __NEXT_DATA__ ou similaire
        for script in soup.find_all("script", type="application/json"):
            try:
                obj = json.loads(script.string or "[]")
                outings = self._find_outings_in_json(obj)
                if outings:
                    return outings
            except (json.JSONDecodeError, TypeError):
                continue

        for script in soup.find_all("script"):
            if not script.string:
                continue
            # Cherche des tableaux d'outings dans le texte
            for match in re.finditer(r'(\[\{[^\[\]]*"_id"[^\[\]]*"name"[^\[\]]*\}\s*(?:,\s*\{[^\[\]]*\}\s*)*\])', script.string):
                try:
                    data = json.loads(match.group(1))
                    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                        if "_id" in data[0] and "name" in data[0]:
                            return data
                except json.JSONDecodeError:
                    continue

        # Balise avec id contenant "data" ou "state"
        for tag in soup.find_all(id=re.compile(r"(__next|data|state|outings)", re.I)):
            if tag.string:
                try:
                    obj = json.loads(tag.string)
                    outings = self._find_outings_in_json(obj)
                    if outings:
                        return outings
                except (json.JSONDecodeError, TypeError):
                    pass
        return None

    def _find_outings_in_json(self, obj) -> Optional[List[Dict]]:
        """Récupère récursivement une liste d'outings dans un objet JSON."""
        if isinstance(obj, list):
            if obj and isinstance(obj[0], dict) and ("_id" in obj[0] or "name" in obj[0]):
                return obj
            for item in obj:
                found = self._find_outings_in_json(item)
                if found:
                    return found
        if isinstance(obj, dict):
            for key in ("outings", "outing", "items", "data", "list"):
                if key in obj and isinstance(obj[key], list) and obj[key]:
                    if isinstance(obj[key][0], dict) and ("_id" in obj[key][0] or "name" in obj[key][0]):
                        return obj[key]
            for v in obj.values():
                found = self._find_outings_in_json(v)
                if found:
                    return found
        return None
    
    def _parse_sorties(self, data: List[Dict]) -> List[Dict]:
        """Parse les sorties depuis les données JSON"""
        sorties = []
        
        for item in data:
            try:
                # Extraction practice (peut être dict ou list)
                practice = item.get('practice', {})
                if isinstance(practice, list) and len(practice) > 0:
                    activite = practice[0].get('name', 'N/A')
                elif isinstance(practice, dict):
                    activite = practice.get('name', 'N/A')
                else:
                    activite = 'N/A'
                
                # Extraction location/address
                address = item.get('address', {})
                if isinstance(address, dict):
                    lieu = address.get('city', 'N/A')
                else:
                    lieu = 'N/A'
                
                # Extraction places disponibles
                participation = item.get('participationCounts', {})
                subscribed = participation.get('subscribed', '?')
                max_seats = item.get('maxSeats', '?')
                places = f"{subscribed} / {max_seats}"
                
                # Extraction encadrant (supervisor)
                supervisor = item.get('supervisor', {})
                contact = 'N/A'
                if isinstance(supervisor, dict) and '_id' in supervisor:
                    contact = 'Encadrant inscrit'
                
                sortie = {
                    'id': f"ffcam_{item.get('_id', '')}",
                    'activite': activite,
                    'titre': item.get('name', 'N/A'),  # 'name' pas 'title'
                    'lieu': lieu,
                    'date': item.get('startDate', ''),
                    'niveau_physique': 'N/A',
                    'niveau_technique': 'N/A',
                    'places': places,
                    'contact': contact,
                    'url': f"{self.base_url}/sortie/{item.get('_id', '')}"
                }
                
                sorties.append(sortie)
                
            except Exception as e:
                print(f"❌ Erreur parsing sortie: {e}")
                continue
        
        return sorties


def main():
    """Test du scraper"""
    scraper = FFCAMScraper(data_dir="data")
    if scraper.has_auth():
        sorties = scraper.scrape_sorties()
        print(f"\n📊 Résultat: {len(sorties)} sorties")
        if sorties:
            print("\n🎯 Première sortie:")
            print(json.dumps(sorties[0], indent=2, ensure_ascii=False))
    else:
        print("\n⚠️ Colle le header Cookie depuis DevTools (sur sorties.ffcam.fr) dans ffcam_cookies.txt")


if __name__ == "__main__":
    main()
