#!/usr/bin/env python3
"""
FFCAM Sorties Scraper
Récupère les sorties depuis la plateforme ALPI (sorties.ffcam.fr) via
l'API publique "for-iframe", la même utilisée par les widgets iframe que
les clubs intègrent sur leur propre site (ex: crest.ffcam.fr/agenda-new.html
qui embarque https://sorties.ffcam.fr/programme/<club_id>).

Cette API ne nécessite AUCUNE authentification : c'est celle utilisée pour
l'affichage public du programme d'un club. Il suffit de connaître l'ID du
club (visible dans l'URL de la page "programme/<club_id>" ou dans le `src`
de l'iframe intégrée sur le site du club).
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests


class FFCAMScraper:
    """Récupère les sorties publiées par un club sur la plateforme ALPI."""

    API_URL_TEMPLATE = "https://api.sorties.ffcam.fr/for-iframe/club/{club_id}/outing"
    PROGRAMME_URL_TEMPLATE = "https://sorties.ffcam.fr/programme/{club_id}"

    # Statuts à conserver par défaut (on ignore les brouillons / annulées)
    DEFAULT_STATUSES = ("published", "validated")

    def __init__(self, club_id: str, club_label: str = "FFCAM", source_key: Optional[str] = None):
        """
        Args:
            club_id: identifiant du club sur la plateforme ALPI
                (ex: "vbmwhyfi9lwjhaxi9mpz" pour Montpellier,
                "m4xrg228iwekrbzijzec" pour Crest). On le trouve dans
                l'URL https://sorties.ffcam.fr/programme/<club_id> ou dans
                le `src` de l'iframe intégrée sur le site du club.
            club_label: nom lisible du club, utilisé pour l'affichage.
            source_key: préfixe utilisé pour générer des IDs uniques et
                distinguer les sources dans l'app. Dérivé de club_label
                si non fourni.
        """
        self.club_id = club_id
        self.club_label = club_label
        self.source_key = source_key or self._slugify(club_label) or club_id[:8]
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })

    @staticmethod
    def _slugify(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (text or "").lower())

    def has_auth(self) -> bool:
        """Conservé pour compatibilité : l'API publique ne nécessite pas d'auth."""
        return True

    def scrape_sorties(self, only_future: bool = True, statuses: Optional[List[str]] = None) -> List[Dict]:
        """Récupère les sorties du club depuis l'API publique ALPI.

        Args:
            only_future: ne garde que les sorties dont la date de début
                n'est pas encore passée.
            statuses: liste des statuts à conserver (défaut: published,
                validated). Passe None ou [] pour tout garder.
        """
        data = self._fetch()
        if not data:
            return []

        sorties = self._parse_sorties(data)

        keep_statuses = self.DEFAULT_STATUSES if statuses is None else statuses
        if keep_statuses:
            sorties = [s for s in sorties if s.get("statut") in keep_statuses]

        if only_future:
            now_iso = datetime.now(timezone.utc).isoformat()
            sorties = [s for s in sorties if not s.get("date") or s["date"] >= now_iso]

        return sorties

    def _fetch(self) -> List[Dict]:
        """Appelle l'API publique for-iframe pour récupérer les sorties brutes."""
        url = self.API_URL_TEMPLATE.format(club_id=self.club_id)
        try:
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("data"), list):
                return data["data"]
            return []
        except Exception as e:
            print(f"❌ Erreur API FFCAM ({self.club_label}): {e}")
            return []

    def _parse_sorties(self, data: List[Dict]) -> List[Dict]:
        """Parse les sorties depuis les données JSON de l'API ALPI."""
        sorties = []

        for item in data:
            try:
                practice = item.get("practice") or {}
                if isinstance(practice, list):
                    activite = practice[0].get("name", "N/A") if practice else "N/A"
                elif isinstance(practice, dict):
                    activite = practice.get("name", "N/A")
                else:
                    activite = "N/A"

                address = item.get("address") or {}
                lieu = address.get("city") if isinstance(address, dict) else None
                if not lieu:
                    departure_address = (item.get("departure") or {}).get("address") or {}
                    lieu = departure_address.get("city")
                lieu = lieu or "N/A"

                participation = item.get("participationCounts") or {}
                subscribed = participation.get("subscribed", "?")
                capacity = item.get("capacity", "?")
                places = f"{subscribed} / {capacity}"

                supervisor = item.get("supervisor") or {}
                if isinstance(supervisor, dict) and (supervisor.get("firstName") or supervisor.get("lastName")):
                    contact = f"{supervisor.get('firstName', '')} {supervisor.get('lastName', '')}".strip()
                else:
                    contact = "N/A"

                outing_id = item.get("_id", "")

                sortie = {
                    "id": f"ffcam_{self.source_key}_{outing_id}",
                    "activite": activite,
                    "titre": item.get("name") or "N/A",
                    "lieu": lieu,
                    "date": item.get("startDate", ""),
                    "niveau_physique": "N/A",
                    "niveau_technique": "N/A",
                    "places": places,
                    "contact": contact,
                    "statut": item.get("status", ""),
                    "url": self.PROGRAMME_URL_TEMPLATE.format(club_id=self.club_id),
                }
                sorties.append(sortie)

            except Exception as e:
                print(f"❌ Erreur parsing sortie FFCAM ({self.club_label}): {e}")
                continue

        return sorties


def main():
    """Test du scraper."""
    import json

    for club_id, label in (
        ("m4xrg228iwekrbzijzec", "CAF Crest"),
        ("vbmwhyfi9lwjhaxi9mpz", "CAF Montpellier"),
    ):
        scraper = FFCAMScraper(club_id=club_id, club_label=label)
        sorties = scraper.scrape_sorties()
        print(f"\n📊 {label}: {len(sorties)} sorties à venir")
        if sorties:
            print(json.dumps(sorties[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
