#!/usr/bin/env python3
"""
Script pour extraire les cookies Chrome de sorties.ffcam.fr
"""

import browser_cookie3
import pickle
from pathlib import Path

def extract_chrome_cookies():
    """Extrait les cookies Chrome pour sorties.ffcam.fr"""
    try:
        print("🔍 Extraction des cookies Chrome pour sorties.ffcam.fr...")
        
        # Charge tous les cookies Chrome
        cj = browser_cookie3.chrome(domain_name='ffcam.fr')
        
        # Filtre les cookies pour sorties.ffcam.fr
        ffcam_cookies = {}
        for cookie in cj:
            if 'ffcam.fr' in cookie.domain:
                ffcam_cookies[cookie.name] = cookie.value
                print(f"  ✓ {cookie.name}: {cookie.value[:20]}...")
        
        if not ffcam_cookies:
            print("❌ Aucun cookie trouvé pour ffcam.fr")
            print("⚠️ Assure-toi d'être connecté à sorties.ffcam.fr dans Chrome")
            return False
        
        # Sauvegarde les cookies
        data_dir = Path("data")
        data_dir.mkdir(parents=True, exist_ok=True)
        cookies_file = data_dir / "ffcam_cookies.pkl"
        
        with open(cookies_file, 'wb') as f:
            pickle.dump(ffcam_cookies, f)
        
        print(f"\n✅ {len(ffcam_cookies)} cookies sauvegardés dans {cookies_file}")
        print("\n📋 Cookies extraits:")
        for name in ffcam_cookies:
            print(f"  - {name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("\n⚠️ Sur macOS, Chrome peut bloquer l'accès aux cookies.")
        print("Solutions:")
        print("1. Redémarre Chrome complètement")
        print("2. Ou utilise la méthode manuelle (DevTools > Application > Cookies)")
        return False

if __name__ == "__main__":
    if extract_chrome_cookies():
        print("\n🎉 Prêt ! Tu peux maintenant lancer le scraper FFCAM.")
    else:
        print("\n💡 Utilise la méthode manuelle dans l'app Streamlit (onglet Scraping)")

