#!/usr/bin/env python3
"""
Configuration des clubs FFCAM suivis (plateforme ALPI - sorties.ffcam.fr).

Chaque club est identifié par l'ID visible dans l'URL de son programme
public (https://sorties.ffcam.fr/programme/<club_id>) ou dans le `src` de
l'iframe intégrée sur le site du club (ex: crest.ffcam.fr/agenda-new.html).

Peut être surchargé via la variable d'environnement FFCAM_CLUBS, au format
"label1:id1,label2:id2".
"""

import os
from typing import List, TypedDict


class ClubConfig(TypedDict):
    key: str
    label: str
    club_id: str


DEFAULT_CLUBS: List[ClubConfig] = [
    {"key": "crest", "label": "CAF Crest", "club_id": "m4xrg228iwekrbzijzec"},
    {"key": "montpellier", "label": "CAF Montpellier", "club_id": "vbmwhyfi9lwjhaxi9mpz"},
]


def _slugify(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def get_clubs() -> List[ClubConfig]:
    """Retourne la liste des clubs à surveiller (env FFCAM_CLUBS ou défaut)."""
    raw = os.getenv("FFCAM_CLUBS", "").strip()
    if not raw:
        return DEFAULT_CLUBS

    clubs: List[ClubConfig] = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        label, club_id = entry.rsplit(":", 1)
        label, club_id = label.strip(), club_id.strip()
        if not label or not club_id:
            continue
        clubs.append({"key": _slugify(label), "label": label, "club_id": club_id})

    return clubs or DEFAULT_CLUBS
