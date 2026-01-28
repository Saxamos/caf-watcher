#!/usr/bin/env python3
"""
FFCAM Sorties Scraper
Récupère les sorties depuis sorties.ffcam.fr via JWT (Authorization).
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
        self.jwt_file = self.data_dir / "ffcam_jwt.txt"
        self.bearer_token: Optional[str] = None
        self._load_jwt()

    def _load_jwt(self):
        """Charge le JWT (access token) depuis le fichier."""
        if self.jwt_file.exists():
            try:
                with open(self.jwt_file, "r") as f:
                    raw = f.read().strip()
                if raw:
                    self.bearer_token = raw.removeprefix("Bearer ").strip()
                    print("✅ JWT FFCAM chargé")
            except Exception as e:
                print(f"⚠️ Erreur chargement JWT: {e}")

    def save_jwt(self, token: str) -> bool:
        """Sauvegarde le JWT (copié depuis DevTools > Network > Request Headers > Authorization)."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            raw = token.strip().removeprefix("Bearer ").strip()
            with open(self.jwt_file, "w") as f:
                f.write(raw)
            self.bearer_token = raw
            print("✅ JWT FFCAM sauvegardé")
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde JWT: {e}")
            return False

    def has_auth(self) -> bool:
        """Indique si un JWT est configuré."""
        return bool(self.bearer_token)

    def _session_headers(self) -> Dict[str, str]:
        """Headers pour les requêtes API (JWT)."""
        h = {
            "Accept": "text/html,application/xhtml+xml,application/json",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        if self.bearer_token:
            h["Authorization"] = f"Bearer {self.bearer_token}"
        return h

    def scrape_sorties(self, max_pages: int = 5) -> List[Dict]:
        """
        Récupère les sorties : d'abord via l'API avec le JWT,
        sinon en parsant la page HTML (fallback).
        """
        if not self.has_auth():
            print("❌ Aucun JWT configuré. Colle le JWT (Authorization) depuis DevTools (sorties.ffcam.fr).")
            return []

        sorties = self._scrape_via_api()
        if sorties:
            return sorties

        sorties = self._scrape_via_page_html()
        return sorties

    def _scrape_via_api(self) -> List[Dict]:
        """Appel API avec le JWT."""
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
                try:
                    err = r.json()
                    msg = err.get("message", err) if isinstance(err, dict) else r.text[:200]
                except Exception:
                    msg = r.text[:200] if r.text else r.reason
                print(f"⚠️ API FFCAM {r.status_code}: {msg}")
                return []
            data = r.json()
            if isinstance(data, list):
                return self._parse_sorties(data)
            return []
        except Exception as e:
            print(f"⚠️ API FFCAM: {e}")
            return []

    def _scrape_via_page_html(self) -> List[Dict]:
        """Charge la page /outing avec le JWT et extrait les sorties du HTML (JSON embarqué)."""
        try:
            r = requests.get(
                self.page_url,
                headers=self._session_headers(),
                timeout=30,
            )
            r.raise_for_status()
            html = r.text

            if "login" in r.url.lower() or "connexion" in html.lower():
                print("❌ JWT expiré ou invalide (page login détectée).")
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
            for match in re.finditer(r'(\[\{[^\[\]]*"_id"[^\[\]]*"name"[^\[\]]*\}\s*(?:,\s*\{[^\[\]]*\}\s*)*\])', script.string):
                try:
                    data = json.loads(match.group(1))
                    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                        if "_id" in data[0] and "name" in data[0]:
                            return data
                except json.JSONDecodeError:
                    continue

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
        """Parse les sorties depuis les données JSON."""
        sorties = []

        for item in data:
            try:
                practice = item.get('practice', {})
                if isinstance(practice, list) and len(practice) > 0:
                    activite = practice[0].get('name', 'N/A')
                elif isinstance(practice, dict):
                    activite = practice.get('name', 'N/A')
                else:
                    activite = 'N/A'

                address = item.get('address', {})
                lieu = address.get('city', 'N/A') if isinstance(address, dict) else 'N/A'

                participation = item.get('participationCounts', {})
                subscribed = participation.get('subscribed', '?')
                max_seats = item.get('maxSeats', '?')
                places = f"{subscribed} / {max_seats}"

                supervisor = item.get('supervisor', {})
                contact = 'Encadrant inscrit' if isinstance(supervisor, dict) and '_id' in supervisor else 'N/A'

                sortie = {
                    'id': f"ffcam_{item.get('_id', '')}",
                    'activite': activite,
                    'titre': item.get('name', 'N/A'),
                    'lieu': lieu,
                    'date': item.get('startDate', ''),
                    'niveau_physique': 'N/A',
                    'niveau_technique': 'N/A',
                    'places': places,
                    'contact': contact,
                    'url': f"{self.base_url}/outing/{item.get('_id', '')}"
                }
                sorties.append(sortie)

            except Exception as e:
                print(f"❌ Erreur parsing sortie: {e}")
                continue

        return sorties


def main():
    """Test du scraper."""
    scraper = FFCAMScraper(data_dir="data")
    if scraper.has_auth():
        sorties = scraper.scrape_sorties()
        print(f"\n📊 Résultat: {len(sorties)} sorties")
        if sorties:
            print("\n🎯 Première sortie:")
            print(json.dumps(sorties[0], indent=2, ensure_ascii=False))
    else:
        print("\n⚠️ Colle le JWT (Authorization) depuis DevTools (sorties.ffcam.fr) dans ffcam_jwt.txt")


if __name__ == "__main__":
    main()
