#!/usr/bin/env python3
"""Longs séjours dans le monde depuis Paris (CDG, Orly), Bruxelles-Zaventem et Amsterdam.
Réglages : config_long.yaml | Historique : dossier data/long/"""
from pathlib import Path

import search

ICI = Path(__file__).parent

if __name__ == "__main__":
    search.main(ICI / "config_long.yaml", ICI / "data" / "long")
