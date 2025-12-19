#!/usr/bin/env python3
"""Script pour lancer le scraper manuellement"""

import sys
import os
from pathlib import Path

# Ajoute le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper import CAFWatcher

if __name__ == "__main__":
    # Utilise /data en Docker, data en local
    data_dir = os.getenv('DATA_DIR', 'data')
    watcher = CAFWatcher(data_dir=data_dir)
    watcher.check_for_updates()

