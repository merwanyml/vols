#!/usr/bin/env python3
"""Détecteur d'offres de vols : cherche, compare, te prévient.

Lancé chaque jour par GitHub Actions (voir .github/workflows/daily.yml).
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
from datetime import date, timedelta
from email.message import EmailMessage
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
HISTORY_FILE = ROOT / "history.json"
NOTIFIED_FILE = ROOT / "notified.json"

JOURS = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6}


# ---------------------------------------------------------------
#  1. Génération des combinaisons (aéroport, destination, dates)
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
    trips = []
    # un départ par semaine, un jour de semaine tiré parmi vendredi/samedi
    for week in range(2, lg["nb_semaines"]):
        d = today + timedelta(weeks=week)
        d = d + timedelta(days=(4 - d.weekday()) % 7)  # vendredi de cette semaine
        mois_longs = lg["mois_longs_sejours"]
        if mois_longs[0] <= d.month <= mois_longs[-1]:
            durees = lg["durees_mois_longs"]
        else:
            durees = lg["durees"]
        for n in durees:
            r = d + timedelta(days=n)
            for o in cfg["aeroports_long_courrier"]:
                for dest in lg["destinations"]:
                    trips.append(("long", o, dest, d, r))
    return trips


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


def search_price(origin, dest, d, r):
    """Retourne (prix_min_en_euros, avis_google) ou None."""
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
    prices = [parse_price(f.price) for f in result.flights]
    prices = [p for p in prices if p]
    if not prices:
        return None
    return min(prices), getattr(result, "current_price", None)


# ---------------------------------------------------------------
#  3. Historique et détection
# ---------------------------------------------------------------
def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def route_key(kind, origin, dest):
    return f"{kind}|{origin}|{dest}"


def evaluate(cfg, kind, price, google_opinion, history_prices):
    """Retourne (est_une_offre, raison, prix_habituel)."""
    det = cfg["detection"]
    seuil_abs = cfg["week_end" if kind == "week_end" else "long_sejour"].get("prix_max_alerte", 0)
    median = None
    if len(history_prices) >= det["echantillon_minimum"]:
        median = statistics.median(history_prices)
        if price <= median * (1 - det["reduction_minimum"] / 100):
            pct = round((1 - price / median) * 100)
            return True, f"{pct}% sous le prix habituel (~{round(median)} €)", median
    if seuil_abs and price <= seuil_abs:
        return True, f"sous ton plafond de {seuil_abs} €", median
    if det.get("utiliser_avis_google") and google_opinion == "low" and median and price <= median * 0.85:
        return True, "Google indique un prix bas", median
    return False, "", median


# ---------------------------------------------------------------
#  4. Notifications (ntfy gratuit, mail en secours)
# ---------------------------------------------------------------
def flights_link(origin, dest, d, r):
    q = f"Flights from {origin} to {dest} on {d} through {r}"
    return "https://www.google.com/travel/flights?q=" + urllib.parse.quote(q)


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
        title = f"{dl['origin']} → {dl['dest']} : {dl['price']} €"
        msg = f"{dl['d']} → {dl['r']} ({dl['kind'].replace('_', '-')}) · {dl['why']}"
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
    history = load_json(HISTORY_FILE, {})
    notified = load_json(NOTIFIED_FILE, {})

    trips = week_end_trips(cfg, today) + long_trips(cfg, today)
    random.shuffle(trips)
    limit = cfg["limites"]["recherches_max"]
    trips = trips[:limit]
    print(f"{len(trips)} recherches prévues")

    deals, ok, fails = [], 0, 0
    for kind, o, dest, d, r in trips:
        if o == dest:
            continue
        try:
            res = search_price(o, dest, d, r)
        except Exception as e:
            fails += 1
            print(f"échec {o}-{dest} {d}: {str(e)[:80]}")
            if fails >= 15 and ok == 0:
                print("Trop d'échecs sans aucun succès : arrêt (Google a peut-être changé).")
                break
            time.sleep(cfg["limites"]["pause_secondes"])
            continue
        time.sleep(cfg["limites"]["pause_secondes"])
        if not res:
            continue
        ok += 1
        price, opinion = res
        key = route_key(kind, o, dest)
        past = [h["p"] for h in history.get(key, [])]
        good, why, median = evaluate(cfg, kind, price, opinion, past)
        history.setdefault(key, []).append({"p": price, "c": today.isoformat()})
        history[key] = history[key][-300:]
        if good:
            nkey = f"{key}|{d}|{r}"
            if nkey not in notified or price < notified[nkey]:
                notified[nkey] = price
                score = (1 - price / median) if median else 0.2
                deals.append({"kind": kind, "origin": o, "dest": dest, "d": d, "r": r,
                              "price": price, "why": why, "score": score,
                              "link": flights_link(o, dest, d, r)})

    print(f"{ok} prix relevés, {fails} échecs, {len(deals)} offre(s)")
    if deals:
        send_alerts(deals, cfg)
    elif os.environ.get("NTFY_TOPIC") and os.environ.get("NTFY_TEST") == "1":
        notify_ntfy(os.environ["NTFY_TOPIC"], "Test", f"Le détecteur fonctionne ({ok} prix relevés).")

    HISTORY_FILE.write_text(json.dumps(history))
    NOTIFIED_FILE.write_text(json.dumps(notified))
    if ok == 0 and trips:
        sys.exit(1)  # fait apparaître l'échec dans GitHub


if __name__ == "__main__":
    main()
