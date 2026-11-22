#!/usr/bin/env python3
"""Revérifie les offres affichées sur le site : le prix est-il toujours d'actualité ?

Pour chaque offre intéressante (proche ou sous le plafond de sa zone), on relance la recherche de ce
voyage précis. Le résultat est noté dans data/verifications/verif-AAAA-MM.csv :
  - baisse    : le prix a baissé  -> l'offre remonte dans « Dernières offres » avec son ancien prix
  - hausse    : le prix a monté   -> le site affiche le nouveau prix (et masque l'offre si elle dépasse
                                     2,5 x le plafond, ou si elle n'est plus sous le plafond dans « Dernières offres »)
  - ok        : prix confirmé
  - introuvable : plus de vol à cet horaire. L'offre n'est masquée qu'après 2 constats d'affilée.
Rien n'est supprimé de la base d'observations : les records et les bilans gardent tout l'historique.
Réglages : bloc « verification » de config_court.yaml et config_long.yaml."""
import csv
import random
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

import bilan
import search

ICI = Path(__file__).parent
DOSSIER = ICI / "data" / "verifications"
COLONNES = "verifie,type,depart,destination,aller,retour,avant,apres,statut,introuvable_n,compagnie"
DEFAUT = {"recherches_max": 200, "pause_secondes": [2.0, 4.5], "echecs_consecutifs_max": 12,
          "duree_max_minutes": 60, "ratio_max": 1.3, "jours": 7}


def cle(r):
    return (r["type"], r["depart"], r["destination"], r["aller"], r["retour"])


def lire_verifications():
    """Dernière vérification de chaque voyage : {(type, depart, dest, aller, retour): dict}."""
    dernieres = {}
    for f in sorted(DOSSIER.glob("verif-*.csv")):
        with f.open(encoding="utf-8") as fh:
            for v in csv.DictReader(fh):
                try:
                    v["avant"], v["apres"] = int(v["avant"]), int(v["apres"])
                    v["introuvable_n"] = int(v["introuvable_n"])
                    dernieres[cle(v)] = v
                except (KeyError, ValueError, TypeError):
                    continue
    return dernieres


def candidats(today):
    """Offres à revérifier, avec leur prix actuel connu, les moins vérifiées d'abord."""
    verifs = lire_verifications()
    liste = []
    for dossier, _, fichier in bilan.SOURCES:
        cfg = yaml.safe_load((ICI / fichier).read_text(encoding="utf-8"))
        reg = {**DEFAUT, "pause_secondes": cfg["limites"]["pause_secondes"], **(cfg.get("verification") or {})}
        derniers = {}
        for r in bilan.lire(ICI / "data" / dossier):   # chronologique : la dernière observation l'emporte
            if (today - r["_rel"]).days <= reg["jours"] and r["_aller"] > today + timedelta(days=1):
                derniers[cle(r)] = r
        for k, r in derniers.items():
            v = verifs.get(k)
            prix = r["prix"]
            if v and v["verifie"] >= r["releve"]:
                if v["statut"] == "introuvable" and v["introuvable_n"] >= 2:
                    continue   # déjà masquée, la recherche normale la fera revenir si elle réapparaît
                if v["statut"] != "introuvable":
                    prix = v["apres"]
            plaf, _ = search.plafond(cfg, bilan.KIND[r["type"]], r["destination"])
            if not plaf or prix > plaf * reg["ratio_max"]:
                continue
            derniere_verif = v["verifie"] if v else ""
            liste.append((derniere_verif, prix / plaf, cfg, reg, r, prix, v))
    liste.sort(key=lambda x: (x[0], x[1]))   # jamais vérifiées d'abord, puis les plus anciennes
    return liste


def main():
    today = date.today()
    liste = candidats(today)
    if not liste:
        print("Aucune offre à vérifier pour l'instant.")
        return
    reg = liste[0][3]
    liste = liste[: reg["recherches_max"]]
    print(f"{len(liste)} offre(s) à vérifier.")
    t0 = time.time()
    sorties, consec_echecs, consec_introuvables = [], 0, 0
    stats = {"ok": 0, "baisse": 0, "hausse": 0, "introuvable": 0, "echec": 0}
    for _, _, cfg, reg, r, avant, v in liste:
        if time.time() - t0 > reg["duree_max_minutes"] * 60:
            print("Durée maximale atteinte, arrêt propre.")
            break
        kind = bilan.KIND[r["type"]]
        section = cfg[search.SECTIONS[kind]]
        directs = bool(section.get("directs_seulement"))
        fen = None
        if kind == "week_end":
            fen = search.fenetre_horaire(((section.get("horaires") or {}).get("depart") or {})
                                         .get(search.JOURS_NOMS[r["_aller"].weekday()]))
        introuvable, res = False, None
        try:
            res = search.search_price(r["depart"], r["destination"], r["_aller"], r["_retour"], directs, fen)
            introuvable = not res or res == search.HORS_HORAIRE
        except Exception as e:
            if search.est_vide(e):
                introuvable = True
            else:
                stats["echec"] += 1
                consec_echecs += 1
                if consec_echecs >= reg["echecs_consecutifs_max"]:
                    print("Trop d'échecs d'affilée : Google freine, arrêt.")
                    break
                search.pause(reg)
                continue
        consec_echecs = 0
        if introuvable:
            consec_introuvables += 1
            n = (v["introuvable_n"] if v and v["statut"] == "introuvable" else 0) + 1
            sorties.append([today.isoformat(), r["type"], r["depart"], r["destination"], r["aller"],
                            r["retour"], avant, avant, "introuvable", n, ""])
            stats["introuvable"] += 1
            if consec_introuvables >= 12:   # probablement un blocage de Google, pas 12 vols disparus
                print("12 vols « introuvables » d'affilée : blocage probable, ces constats sont ignorés.")
                sorties = sorties[:-12]
                break
        else:
            consec_introuvables = 0
            prix, _, info = res
            if prix < avant * 0.97:
                statut = "baisse"
            elif prix > avant * 1.03:
                statut = "hausse"
            else:
                statut = "ok"
            stats[statut] += 1
            cie = str(info.get("compagnie", "")).replace(",", "/")[:40]
            sorties.append([today.isoformat(), r["type"], r["depart"], r["destination"], r["aller"],
                            r["retour"], avant, prix, statut, 0, cie])
        search.pause(reg)
    if sorties:
        DOSSIER.mkdir(parents=True, exist_ok=True)
        f = DOSSIER / f"verif-{today:%Y-%m}.csv"
        neuf = not f.exists()
        with f.open("a", encoding="utf-8") as fh:
            if neuf:
                fh.write(COLONNES + "\n")
            for s in sorties:
                fh.write(",".join(str(x) for x in s) + "\n")
    print(f"Vérifiées : {len(sorties)}. Confirmées {stats['ok']}, en baisse {stats['baisse']}, "
          f"en hausse {stats['hausse']}, introuvables {stats['introuvable']}, échecs {stats['echec']}. "
          f"({(time.time() - t0) / 60:.1f} min)")
    if not sorties and liste:
        sys.exit(1)


if __name__ == "__main__":
    main()
