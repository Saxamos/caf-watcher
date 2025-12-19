#!/usr/bin/env python3
"""
Import des cookies FFCAM depuis le navigateur

INSTRUCTIONS:
1. Connecte-toi à sorties.ffcam.fr dans Chrome/Firefox
2. Ouvre les DevTools (F12)
3. Va dans l'onglet "Network"
4. Rafraîchis la page
5. Clique sur une requête vers sorties.ffcam.fr
6. Copie les cookies depuis les headers (Cookie: ...)
7. Colle-les quand ce script te le demande
"""

import pickle
import sys
from pathlib import Path


def parse_cookie_string(cookie_string: str) -> dict:
    """Parse une chaîne de cookies"""
    cookies = {}
    for item in cookie_string.split(';'):
        item = item.strip()
        if '=' in item:
            name, value = item.split('=', 1)
            cookies[name.strip()] = value.strip()
    return cookies


def main():
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    cookies_file = data_dir / "ffcam_cookies.pkl"
    
    print("=" * 60)
    print("🍪 IMPORT DES COOKIES FFCAM")
    print("=" * 60)
    print()
    print("📝 INSTRUCTIONS:")
    print("1. Connecte-toi à https://sorties.ffcam.fr dans ton navigateur")
    print("2. Ouvre les DevTools (F12)")
    print("3. Va dans l'onglet 'Application' (Chrome) ou 'Storage' (Firefox)")
    print("4. Sélectionne 'Cookies' > 'https://sorties.ffcam.fr'")
    print("5. Cherche les cookies importants (comme 'session', 'auth', etc.)")
    print()
    print("ALTERNATIVE (plus simple):")
    print("1. Connecte-toi à https://sorties.ffcam.fr")
    print("2. Ouvre DevTools > Network")
    print("3. Rafraîchis la page")
    print("4. Clique sur une requête vers sorties.ffcam.fr")
    print("5. Dans 'Request Headers', copie la valeur du header 'Cookie:'")
    print()
    print("=" * 60)
    print()
    
    # Méthode 1: Coller toute la ligne Cookie
    print("📋 Colle ici toute la ligne de cookies:")
    print("   (format: name1=value1; name2=value2; ...)")
    print()
    cookie_string = input("Cookies: ").strip()
    
    if not cookie_string:
        print("❌ Aucun cookie fourni")
        sys.exit(1)
    
    # Parse les cookies
    cookies = parse_cookie_string(cookie_string)
    
    if not cookies:
        print("❌ Impossible de parser les cookies")
        sys.exit(1)
    
    print(f"\n✅ {len(cookies)} cookies détectés:")
    for name in cookies.keys():
        print(f"   • {name}")
    
    # Sauvegarde
    try:
        # Crée un jar de cookies requests
        import requests
        session = requests.Session()
        
        for name, value in cookies.items():
            session.cookies.set(name, value, domain='.ffcam.fr')
        
        with open(cookies_file, 'wb') as f:
            pickle.dump(session.cookies, f)
        
        print(f"\n💾 Cookies sauvegardés dans {cookies_file}")
        print()
        print("✅ Configuration terminée!")
        print()
        print("🧪 Pour tester:")
        print("   uv run python -m src.ffcam_scraper")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la sauvegarde: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

