#!/usr/bin/env python3
"""Bilan de la semaine : meilleurs billets du court et du long courrier, comparés à tout ce que le
journal d'observations (data/court/obs-*.csv et data/long/obs-*.csv) a enregistré avant.

Il écrit un rapport dans data/bilans/ et envoie un résumé sur ton téléphone (ntfy) et par mail
si Gmail est configuré. Lancé automatiquement chaque dimanche (workflow bilan.yml)."""
import csv
import os
import statistics
from datetime import date, timedelta
from pathlib import Path

import yaml

import couts
import search
from noms import nom

ICI = Path(__file__).parent
SOURCES = [
    ("court", "COURT COURRIER (week-ends et vacances)", "config_court.yaml"),
    ("long", "LONG COURRIER", "config_long.yaml"),
]
KIND = {"w": "week_end", "v": "vacances", "l": "long"}
LABEL = {"w": "week-end", "v": "vacances", "l": "long séjour"}
TOP = 5


def lire(dossier):
    rows = []
    for f in sorted(dossier.glob("obs-*.csv")):
        with f.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    r["prix"] = int(r["prix"])
                    r["_rel"] = date.fromisoformat(r["releve"])
                    r["_aller"] = date.fromisoformat(r["aller"])
                    r["_retour"] = date.fromisoformat(r["retour"])
                    rows.append(r)
                except (KeyError, ValueError, TypeError):
                    continue
    return rows


def cle_route(cfg, r):
    """Une route = type + départ + destination (+ période pour le long courrier : les prix
    d'avril, d'été et de Noël ne se comparent pas entre eux)."""
    per = search.periode_de(cfg, r["_aller"]) if r["type"] == "l" else ""
    return (r["type"], r["depart"], r["destination"], per)


def euros(x):
    return f"{round(x)} €"


def analyser(nom_dossier, titre, fichier_cfg, today):
    cfg = yaml.safe_load((ICI / fichier_cfg).read_text(encoding="utf-8"))
    rows = lire(ICI / "data" / nom_dossier)
    md, court = [f"## {titre}", ""], [titre]
    if not rows:
        md.append("Pas encore de données : le journal d'observations est vide.\n")
        court.append("Pas encore de données.")
        return md, court
    debut_sem = today - timedelta(days=7)
    sem = [r for r in rows if r["_rel"] > debut_sem]
    avant = [r for r in rows if r["_rel"] <= debut_sem]
    historique = {}
    for r in avant:
        historique.setdefault(cle_route(cfg, r), []).append(r["prix"])
    premier = min(r["_rel"] for r in rows)
    jours_donnees = (today - premier).days + 1

    # ---------- couverture ----------
    routes_sem = {cle_route(cfg, r) for r in sem}
    dests_sem = {r["destination"] for r in sem}
    md.append(f"**Cette semaine** : {len(sem)} prix relevés sur {len(routes_sem)} routes "
              f"({len(dests_sem)} destinations). Données accumulées depuis {jours_donnees} jours "
              f"({len(rows)} relevés).\n")
    court.append(f"{len(sem)} prix relevés, {len(dests_sem)} destinations, {jours_donnees} j d'historique.")

    # ---------- meilleurs billets ----------
    meilleurs = {}
    for r in sem:
        k = cle_route(cfg, r)
        if k not in meilleurs or r["prix"] < meilleurs[k]["prix"]:
            meilleurs[k] = r
    lignes = []
    for k, r in meilleurs.items():
        plaf, zone = search.plafond(cfg, KIND[r["type"]], r["destination"])
        ratio = r["prix"] / plaf if plaf else 9.9
        lignes.append((ratio, k, r, plaf, zone))
    lignes.sort(key=lambda x: x[0])
    vus, top = set(), []
    for ratio, k, r, plaf, zone in lignes:   # une seule ligne par destination (meilleur aéroport de départ)
        if (k[2], k[3]) in vus:
            continue
        vus.add((k[2], k[3]))
        top.append((ratio, k, r, plaf, zone))
        if len(top) == TOP:
            break

    md.append(f"### Top {TOP} des billets de la semaine")
    md.append("_Classés par rapport au plafond de leur zone (distance), pas par rapport à un prix "
              "« habituel » qui peut être gonflé._\n")
    for i, (ratio, k, r, plaf, zone) in enumerate(top, 1):
        o, dest = r["depart"], r["destination"]
        nuits = (r["_retour"] - r["_aller"]).days
        hist = historique.get(k, [])
        txt = (f"{i}. **{nom(o)} ⇄ {nom(dest)} : {r['prix']} € A/R** · "
               f"{search.jour_fr(r['_aller'])} → {search.jour_fr(r['_retour'])} · {nuits} nuits "
               f"({LABEL[r['type']]})")
        if r["compagnie"]:
            txt += f" · {r['compagnie']}"
        sous = []
        sous.append(("✅ sous" if r["prix"] <= plaf else "au-dessus du") + f" plafond {plaf} € ({zone})")
        if hist:
            rec, med = min(hist), statistics.median(hist)
            if r["prix"] < rec:
                sous.append(f"🏆 bat le record des semaines précédentes ({rec} €) de {round((1 - r['prix'] / rec) * 100)} %")
            else:
                sous.append(f"record précédent {rec} € · prix médian relevé {round(med)} € ({len(hist)} relevés)")
        else:
            sous.append("première semaine de données sur cette route")
        hotel = couts.hotel_nuit(dest, r["_aller"].month)
        total, detail = r["prix"], []
        if hotel:
            total += hotel * nuits
            detail.append(f"hôtel {nuits}×{hotel} €")
        if r["type"] != "l" and dest in couts.TRANSFERT:
            moyen, tr = couts.TRANSFERT[dest]
            total += tr
            detail.append(f"transferts {tr:g} € ({moyen})")
        if detail:
            sous.append(f"séjour estimé ≈ **{round(total)} € par personne** = vol {r['prix']} € + " + " + ".join(detail)
                        + f" ({couts.ESTIMATION})")
        lien = search.lien_vol(o, dest, r["_aller"], r["_retour"], r["type"] != "l")
        md.append(txt)
        for s in sous:
            md.append(f"   - {s}")
        md.append(f"   - [Voir sur Google Flights]({lien}) _(prix vu le {r['releve']}, à revérifier)_")
        court.append(f"{i}. {nom(o)}⇄{nom(dest)} {r['prix']}€ {search.jour_fr(r['_aller'])}→{search.jour_fr(r['_retour'])}"
                     + (f" (≈{round(total)}€ tout compris)" if detail else "")
                     + (" ✅" if r["prix"] <= plaf else ""))
    md.append("")

    # ---------- évolution par zone ----------
    par_zone = {}   # zone -> semaine (0 = cette semaine) -> route -> prix minimum
    for r in rows:
        sem_i = (today - r["_rel"]).days // 7
        if sem_i > 4:
            continue
        zone = search.plafond(cfg, KIND[r["type"]], r["destination"])[1]
        d = par_zone.setdefault(zone, {}).setdefault(sem_i, {})
        k = cle_route(cfg, r)
        d[k] = min(d.get(k, 10 ** 9), r["prix"])
    md.append("### Évolution des prix par zone")
    md.append("_Prix médian du meilleur billet de chaque route, semaine par semaine "
              "(plus la valeur est basse, mieux c'est)._\n")
    md.append("| Zone | Cette semaine | S-1 | S-2 | S-3 | S-4 | Tendance |")
    md.append("|---|---|---|---|---|---|---|")
    for zone, semaines in sorted(par_zone.items()):
        cells, vals = [], {}
        for i in range(5):
            if i in semaines:
                vals[i] = statistics.median(semaines[i].values())
                cells.append(euros(vals[i]))
            else:
                cells.append("–")
        prec = [vals[i] for i in range(1, 5) if i in vals]
        tend = "–"
        if 0 in vals and prec:
            var = (vals[0] / statistics.mean(prec) - 1) * 100
            tend = f"{var:+.0f} %" + (" 📉" if var <= -10 else (" 📈" if var >= 10 else ""))
        md.append(f"| {zone} | " + " | ".join(cells) + f" | {tend} |")
    md.append("")

    # ---------- réglages suggérés ----------
    md.append("### Réglages suggérés")
    if jours_donnees < 14:
        md.append(f"Pas encore assez de données ({jours_donnees} jours) : il en faut au moins 14 pour "
                  "juger les plafonds. Reviens voir dans une ou deux semaines.\n")
    else:
        sugg = []
        recents = [r for r in rows if (today - r["_rel"]).days < 28]
        meilleur_route = {}
        n_route = {}
        for r in recents:
            k = cle_route(cfg, r)
            meilleur_route[k] = min(meilleur_route.get(k, 10 ** 9), r["prix"])
            n_route[k] = n_route.get(k, 0) + 1
        zones = {}
        for k, p in meilleur_route.items():
            plaf, zone = search.plafond(cfg, KIND[k[0]], k[2])
            zones.setdefault(zone, []).append((k, p, plaf))
        for zone, lst in sorted(zones.items()):
            plaf = lst[0][2]
            if not plaf or len(lst) < 5:
                continue
            prix = [p for _, p, _ in lst]
            med = statistics.median(prix)
            sous = sum(1 for p in prix if p <= plaf)
            if sous == 0 and med > 1.5 * plaf:
                sugg.append(f"**{zone}** : plafond de {plaf} € jamais atteint en 4 semaines (médiane des meilleurs prix "
                            f"{round(med)} €, minimum {min(prix)} €). Soit une vraie bonne affaire n'est pas encore "
                            f"passée, soit le plafond est trop bas pour cette zone : à ajuster vers ~{round(min(prix) * 1.1 / 10) * 10} € "
                            "si tu veux être prévenu plus souvent.")
            elif sous / len(lst) >= 0.3:
                sugg.append(f"**{zone}** : plafond de {plaf} € atteint sur {round(100 * sous / len(lst))} % des routes : "
                            "probablement trop large (trop de notifications). Baisse-le.")
            loin = [k for k, p, _ in lst if p > 2.5 * plaf and n_route[k] >= 10]
            if len(loin) >= 3:
                ex = ", ".join(f"{nom(k[1])}→{nom(k[2])}" for k in loin[:4])
                sugg.append(f"**{zone}** : {len(loin)} routes ne descendent jamais sous 2,5 × le plafond (ex. {ex}). "
                            "Candidates à surveiller moins ou à retirer.")
        md.extend(f"- 💡 {s}" for s in sugg) if sugg else md.append("Aucun ajustement à proposer pour l'instant.")
        md.append("")
        if sugg:
            court.append(f"{len(sugg)} réglage(s) suggéré(s) (voir le rapport).")
    return md, court


def main():
    today = date.today()
    md = [f"# Bilan de la semaine du {today:%d/%m/%Y}", ""]
    court = [f"📊 Bilan du {today:%d/%m}"]
    for dossier, titre, cfg in SOURCES:
        m, c = analyser(dossier, titre, cfg, today)
        md += m
        court += [""] + c
    md += ["---",
           f"_Transferts et hôtels : {couts.ESTIMATION}, par personne, chambre double partagée. "
           "Les prix des vols sont ceux vus par Google Flights au moment du relevé._"]
    texte = "\n".join(md)
    sortie = ICI / "data" / "bilans"
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / f"bilan-{today.isoformat()}.md").write_text(texte, encoding="utf-8")
    print(texte)

    topic = os.environ.get("NTFY_TOPIC")
    message = "\n".join(court)[:3800] + "\n\nRapport complet dans le dossier data/bilans du dépôt."
    if topic:
        try:
            search.notify_ntfy(topic, "📊 Bilan de la semaine", message)
        except Exception as e:
            print("ntfy erreur:", e)
    try:
        search.notify_mail(f"📊 Bilan de la semaine du {today:%d/%m}", texte)
    except Exception as e:
        print("mail erreur:", e)


if __name__ == "__main__":
    main()
