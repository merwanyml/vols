#!/usr/bin/env python3
"""Week-ends en Europe depuis Lille, Paris-Beauvais et Bruxelles-Charleroi.
Réglages : config_court.yaml | Historique : dossier data/court/"""
from pathlib import Path

import search

ICI = Path(__file__).parent

if __name__ == "__main__":
    search.main(ICI / "config_court.yaml", ICI / "data" / "court")
