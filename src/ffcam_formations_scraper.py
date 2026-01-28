#!/usr/bin/env python3
"""
Scraper des formations FFCAM (agenda fédéral)
Source: https://www.ffcam.fr/les-formations.html
"""

import re
from typing import List, Dict
import requests
from bs4 import BeautifulSoup


class FFCAMFormationsScraper:
    """Récupère les formations depuis l'agenda fédéral FFCAM."""

    BASE_URL = "https://www.ffcam.fr"
    FORMATIONS_URL = "https://www.ffcam.fr/les-formations.html"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        })

    def scrape_formations(self) -> List[Dict]:
        """Scrape toutes les formations de l'agenda fédéral."""
        try:
            r = self.session.get(self.FORMATIONS_URL, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            formations = []
            # Chaque formation est dans un span.infos.clearfix contenant span.titre + div.ffcam-formation
            infos_blocks = soup.find_all("span", class_="infos")
            for block in infos_blocks:
                titre_span = block.find("span", class_="titre")
                form_div = block.find("div", class_="ffcam-formation")
                if not titre_span or not form_div:
                    continue

                title = titre_span.get_text(strip=True)
                text = form_div.get_text(separator="\n", strip=True)

                ref_match = re.search(r"Référence du stage:\s*([A-Z0-9]+)", text, re.I)
                ref = ref_match.group(1) if ref_match else None
                if not ref:
                    continue

                def extract_field(pattern: str, default: str = "N/A") -> str:
                    m = re.search(pattern, text, re.I | re.DOTALL)
                    return m.group(1).strip() if m else default

                date_str = extract_field(r"Dates?:\s*(.+?)(?=\n[A-Z]|\n\n|$)")
                lieu = extract_field(r"Lieu:\s*(.+?)(?=\n[A-Z]|\n\n|$)")
                discipline = extract_field(r"Discipline:\s*(.+?)(?=\n[A-Z]|\n\n|$)")
                participants = extract_field(r"Nombre de participants:\s*(\d+)", "?")
                places_restantes = re.search(r"Places restantes:\s*(\d+)", text, re.I)
                places_rest = places_restantes.group(1) if places_restantes else "?"
                responsable = extract_field(r"Responsable du stage:\s*(.+?)(?=\n[A-Z]|\n\n|$)")

                # Lien vers la page formations (pas de lien direct par formation sur le site)
                url = self.FORMATIONS_URL

                sortie = {
                    "id": f"ffcam_form_{ref}",
                    "activite": discipline,
                    "titre": title,
                    "lieu": lieu,
                    "date": date_str,
                    "niveau_physique": 0,
                    "niveau_technique": 0,
                    "places": f"{participants} places ({places_rest} restantes)" if participants != "?" else "N/A",
                    "contact": responsable,
                    "url": url,
                }
                formations.append(sortie)

            return formations

        except Exception as e:
            print(f"❌ Erreur scraping formations FFCAM: {e}")
            return []


def main():
    scraper = FFCAMFormationsScraper()
    formations = scraper.scrape_formations()
    print(f"📚 {len(formations)} formations récupérées")
    if formations:
        print("Exemple:", formations[0]["titre"], "|", formations[0]["date"], "|", formations[0]["lieu"])


if __name__ == "__main__":
    main()
