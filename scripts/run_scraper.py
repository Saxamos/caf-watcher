#!/usr/bin/env python3
"""Script pour lancer le scraper manuellement"""

import sys
from pathlib import Path

# Ajoute le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper import CAFWatcher

if __name__ == "__main__":
    watcher = CAFWatcher(data_dir="data")
    watcher.check_for_updates()

