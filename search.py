#!/usr/bin/env python3
"""Détecteur d'offres de vols : cherche, compare, te prévient.

Lancé plusieurs fois par jour par GitHub Actions (voir .github/workflows/daily.yml).
Tout se règle dans config.yaml.
"""
import json
import os
import random
import re
import smtplib
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

import yaml

from noms import nom

ROOT = Path(__file__).parent
HISTORY_FILE = ROOT / "history.json"    # prix relevés par route
NOTIFIED_FILE = ROOT / "notified.json"  # offres déjà signalées
VUS_FILE = ROOT / "vus.json"            # date de la dernière recherche de chaque combinaison

JOURS = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6}
JOURS_ABR = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]


def jour_fr(d):
    return f"{JOURS_ABR[d.weekday()]} {d.day:02d}/{d.month:02d}"


# ---------------------------------------------------------------
#  1. Génération des combinaisons (type, départ, destination, aller, retour)
# ---------------------------------------------------------------
def week_end_trips(cfg, today):
    wk = cfg["week_end"]
    if not wk.get("actif"):
        return []
    departs = [JOURS[j] for j in wk["departs"]]
    retours = [JOURS[j] for j in wk["retours"]]
    trips = []
    for offset in range(1, wk["nb_semaines"] * 7):
        d = today + timedelta(days=offset)
        if d.weekday() not in departs:
            continue
        for k in range(1, 5):
            r = d + timedelta(days=k)
            if r.weekday() in retours:
                for o in cfg["aeroports_week_end"]:
                    for dest in wk["destinations"]:
                        trips.append(("week_end", o, dest, d, r))
    return trips


def long_trips(cfg, today):
    lg = cfg["long_sejour"]
    if not lg.get("actif"):
        return []
    first = today + timedelta(days=2)
    last = today + timedelta(days=330)  # Google n'affiche pas plus loin
    trips = []
    for p in lg["periodes"]:
        debut = date.fromisoformat(str(p["debut"]))
        fin = date.fromisoformat(str(p["fin"]))
        pas = max(1, int(p.get("pas_jours", 1)))
        d = debut
        while d <= fin:
            if first <= d <= last:
                for n in p["durees"]:
                    r = d + timedelta(days=n)
                    if r <= fin:
                        for o in cfg["aeroports_long_courrier"]:
                            for dest in lg["destinations"]:
                                trips.append(("long", o, dest, d, r))
            d += timedelta(days=pas)
    return trips


def combo_key(t):
    kind, o, dest, d, r = t
    return f"{kind[0]}|{o}|{dest}|{d:%y%m%d}|{r:%y%m%d}"


def pick(trips, n, vus):
    """Prend les n combinaisons cherchées le moins récemment (jamais cherchées d'abord).
    Résultat : tout est couvert avant de refaire deux fois la même recherche,
    même avec plusieurs lancements par jour."""
    if n <= 0 or not trips:
        return []
    rnd = random.Random()
    return sorted(trips, key=lambda t: (vus.get(combo_key(t), ""), rnd.random()))[:n]


# ---------------------------------------------------------------
#  2. Recherche des prix (Google Flights via fast-flights, gratuit)
# ---------------------------------------------------------------
def parse_price(text):
    if text is None:
        return None
    s = re.sub(r"[^\d.,]", "", str(text))
    s = re.sub(r"[.,]\d{1,2}$", "", s)  # retire les centimes éventuels
    digits = re.sub(r"[.,]", "", s)     # retire les séparateurs de milliers
    return int(digits) if digits else None


def search_price(origin, dest, d, r, directs=False):
    """Retourne (prix_aller_retour_min, avis_google, devise) ou None."""
    from fast_flights import FlightData, Passengers, get_flights

    result = get_flights(
        flight_data=[
            FlightData(date=d.isoformat(), from_airport=origin, to_airport=dest),
            FlightData(date=r.isoformat(), from_airport=dest, to_airport=origin),
        ],
        trip="round-trip",
        seat="economy",
        passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
        fetch_mode="fallback",
    )
    flights = list(result.flights)
    if directs:
        flights = [f for f in flights if str(getattr(f, "stops", 0)) in ("0", "None")]
    raws = [f.price for f in flights]
    prices = [parse_price(x) for x in raws]
    prices = [p for p in prices if p]
    if not prices:
        return None
    first = str(raws[0])
    devise = "$" if "$" in first else "£" if "£" in first else "€"
    return min(prices), getattr(result, "current_price", None), devise


# ---------------------------------------------------------------
#  3. Historique et détection
# ---------------------------------------------------------------
def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def save_json(path, data):
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False))


def route_key(kind, origin, dest):
    return f"{kind}|{origin}|{dest}"


def plafond(cfg, kind, dest):
    """Plafond d'alerte selon la zone de destination (la distance, pas la durée)."""
    for z in cfg.get("zones", []):
        if dest in z["destinations"]:
            return z["plafond"], z["nom"]
    return cfg["week_end" if kind == "week_end" else "long_sejour"].get("prix_max_alerte", 0), "plafond par défaut"


def evaluate(cfg, kind, dest, price, google_opinion, history_prices):
    """Retourne (est_une_offre, raison, prix_habituel)."""
    det = cfg["detection"]
    seuil_abs, zone = plafond(cfg, kind, dest)
    median = None
    if len(history_prices) >= det["echantillon_minimum"]:
        median = statistics.median(history_prices)
        if price <= median * (1 - det["reduction_minimum"] / 100):
            pct = round((1 - price / median) * 100)
            return True, f"{pct}% sous le prix habituel (~{round(median)} €)", median
    if seuil_abs and price <= seuil_abs:
        return True, f"sous ton plafond de {seuil_abs} € ({zone})", median
    if det.get("utiliser_avis_google") and google_opinion == "low" and median and price <= median * 0.85:
        return True, "Google indique un prix bas", median
    return False, "", median


# ---------------------------------------------------------------
#  4. Notifications (ntfy gratuit, mail en secours)
# ---------------------------------------------------------------
def flights_link(origin, dest, d, r):
    q = f"Flights from {origin} to {dest} on {d} through {r}"
    return "https://www.google.com/travel/flights?hl=fr&curr=EUR&q=" + urllib.parse.quote(q)


def notify_ntfy(topic, title, message, click=None):
    payload = {"topic": topic, "title": title, "message": message, "tags": ["airplane"]}
    if click:
        payload["click"] = click
    req = urllib.request.Request(
        "https://ntfy.sh",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=20).read()


def notify_mail(subject, body):
    user = os.environ.get("GMAIL_USER")
    pwd = os.environ.get("GMAIL_APP_PASSWORD")
    if not (user and pwd):
        return
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = os.environ.get("MAIL_TO", user)
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pwd)
        s.send_message(msg)


def send_alerts(deals, cfg):
    topic = os.environ.get("NTFY_TOPIC")
    deals = sorted(deals, key=lambda x: x["score"], reverse=True)[: cfg["limites"]["max_notifications"]]
    lines = []
    for dl in deals:
        title = f"{nom(dl['origin'])} ⇄ {nom(dl['dest'])} : {dl['price']} {dl['devise']} A/R"
        nuits = (dl["r"] - dl["d"]).days
        type_ = "week-end" if dl["kind"] == "week_end" else "long séjour"
        msg = (f"💶 {dl['price']} {dl['devise']} l'aller-retour\n"
               f"{jour_fr(dl['d'])} → {jour_fr(dl['r'])} · {nuits} nuits ({type_})\n"
               f"{dl['why']}")
        lines.append(f"{title}\n{msg}\n{dl['link']}\n")
        if topic:
            try:
                notify_ntfy(topic, title, msg, dl["link"])
            except Exception as e:  # une notif ratée ne doit pas tout casser
                print("ntfy erreur:", e)
    if deals:
        notify_mail(f"✈️ {len(deals)} bonne(s) offre(s) de vol", "\n".join(lines))


# ---------------------------------------------------------------
#  5. Programme principal
# ---------------------------------------------------------------
def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    today = date.today()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
    history = load_json(HISTORY_FILE, {})
    notified = load_json(NOTIFIED_FILE, {})
    vus = load_json(VUS_FILE, {})
    lim = cfg["limites"]
    vides = history.setdefault("_vides", {})

    # on oublie les combinaisons dont le départ est passé
    limite_passe = f"{today:%y%m%d}"
    vus = {k: v for k, v in vus.items() if k.split("|")[3] >= limite_passe}

    def route_ok(t):
        v = vides.get(route_key(t[0], t[1], t[2]))
        if not v or v["n"] < lim["routes_vides_avant_pause"]:
            return True
        return (today - date.fromisoformat(v["d"])).days >= lim["routes_vides_jours_pause"]

    wk = [t for t in week_end_trips(cfg, today) if route_ok(t)]
    lg = [t for t in long_trips(cfg, today) if route_ok(t)]
    n_wk = lim["recherches_max"] if not lg else int(lim["recherches_max"] * lim["part_week_end"])
    n_lg = lim["recherches_max"] - n_wk if lg else 0
    trips = pick(wk, n_wk, vus) + pick(lg, n_lg, vus)
    random.shuffle(trips)
    print(f"{len(trips)} recherches prévues ({len(wk)} week-end et {len(lg)} longs séjours possibles)")

    sans_zone = sorted({t[2] for t in wk + lg
                        if not any(t[2] in z["destinations"] for z in cfg.get("zones", []))})
    if sans_zone:
        print("Destinations sans zone de plafond (plafond par défaut utilisé):", ", ".join(sans_zone))

    t0 = time.time()
    deals, ok, fails = [], 0, 0
    empties, succeeded = [], set()
    for t in trips:
        kind, o, dest, d, r = t
        if time.time() - t0 > lim["duree_max_minutes"] * 60:
            print("Durée maximale atteinte, arrêt propre.")
            break
        if o == dest:
            continue
        directs = bool(cfg["week_end" if kind == "week_end" else "long_sejour"].get("directs_seulement"))
        try:
            res = search_price(o, dest, d, r, directs)
        except Exception as e:
            fails += 1
            print(f"échec {o}-{dest} {d}: {str(e)[:80]}")
            if fails >= 15 and ok == 0:
                print("Trop d'échecs sans aucun succès : arrêt (Google a peut-être changé).")
                break
            time.sleep(lim["pause_secondes"])
            continue
        time.sleep(lim["pause_secondes"])
        key = route_key(kind, o, dest)
        vus[combo_key(t)] = now
        if not res:
            empties.append(key)
            continue
        ok += 1
        succeeded.add(key)
        vides.pop(key, None)
        price, opinion, devise = res
        if devise != "€":
            print(f"Attention : prix en {devise} reçu pour {o}-{dest}")
        past = [h["p"] for h in history.get(key, [])]
        good, why, median = evaluate(cfg, kind, dest, price, opinion, past)
        history.setdefault(key, []).append({"p": price, "c": today.isoformat()})
        history[key] = history[key][-300:]
        if good:
            nkey = f"{key}|{d}|{r}"
            if nkey not in notified or price < notified[nkey]:
                notified[nkey] = price
                score = (1 - price / median) if median else 0.2
                deals.append({"kind": kind, "origin": o, "dest": dest, "d": d, "r": r,
                              "price": price, "devise": devise, "why": why, "score": score,
                              "link": flights_link(o, dest, d, r)})

    # Routes sans aucun vol : on ne les met de côté que si ce n'est pas un blocage de Google
    total = ok + len(empties)
    if total >= 30 and len(empties) / total > 0.6:
        print("Beaucoup de recherches vides : Google bloque peut-être. Aucune route mise de côté.")
    else:
        for key in empties:
            if key in succeeded:
                continue
            v = vides.setdefault(key, {"n": 0, "d": today.isoformat()})
            v["n"] += 1
            v["d"] = today.isoformat()

    mins = (time.time() - t0) / 60
    cadence = f"{mins * 60 / max(1, total):.1f} s par recherche" if total else ""
    print(f"{ok} prix relevés, {len(empties)} sans résultat, {fails} échecs, "
          f"{len(deals)} offre(s) en {mins:.1f} min. {cadence}")
    paused = sum(1 for v in vides.values() if v["n"] >= lim["routes_vides_avant_pause"])
    print(f"Routes actuellement mises de côté : {paused}")

    if deals:
        send_alerts(deals, cfg)
    elif os.environ.get("NTFY_TOPIC") and os.environ.get("NTFY_TEST") == "1":
        notify_ntfy(os.environ["NTFY_TOPIC"], "Test", f"Le détecteur fonctionne ({ok} prix relevés).")

    save_json(HISTORY_FILE, history)
    save_json(NOTIFIED_FILE, notified)
    save_json(VUS_FILE, vus)
    if ok == 0 and trips:
        sys.exit(1)  # fait apparaître l'échec dans GitHub


if __name__ == "__main__":
    main()
