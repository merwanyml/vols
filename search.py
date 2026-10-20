#!/usr/bin/env python3
"""Moteur de recherche d'offres de vols.

Il est utilisé par deux petits scripts :
  - court_courrier.py  (week-ends depuis Lille, Beauvais, Charleroi)
  - long_courrier.py   (longs séjours depuis Paris)
Chacun a sa configuration (config_court.yaml / config_long.yaml) et son propre historique.
"""
import base64
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

JOURS = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6}
JOURS_ABR = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
JOURS_NOMS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def jour_fr(d):
    return f"{JOURS_ABR[d.weekday()]} {d.day:02d}/{d.month:02d}"


# ---------------------------------------------------------------
#  1. Génération des combinaisons (type, départ, destination, aller, retour)
# ---------------------------------------------------------------
def week_end_trips(cfg, today):
    wk = cfg.get("week_end", {})
    if not wk.get("actif"):
        return []
    departs = [JOURS[j] for j in wk["departs"]]
    retours = [JOURS[j] for j in wk["retours"]]
    # retours supplémentaires acceptés seulement à partir d'une date (ex. lundi dès janvier)
    sup = wk.get("retours_supplementaires") or {}
    sup_date = date.fromisoformat(str(sup["a_partir_du"])) if sup else None
    sup_jours = [JOURS[j] for j in sup.get("jours", [])]
    # destinations : liste explicite, sinon toutes celles des zones
    dests = wk.get("destinations") or [d for z in cfg.get("zones", []) for d in z["destinations"]]
    trips = []
    for offset in range(1, wk["nb_semaines"] * 7):
        d = today + timedelta(days=offset)
        if d.weekday() not in departs:
            continue
        for k in range(1, 5):
            r = d + timedelta(days=k)
            if r.weekday() in retours or (sup and r >= sup_date and r.weekday() in sup_jours):
                for o in cfg["aeroports_week_end"]:
                    for dest in dests:
                        trips.append(("week_end", o, dest, d, r))
    return trips


def long_trips(cfg, today):
    lg = cfg.get("long_sejour", {})
    if not lg.get("actif"):
        return []
    first = today + timedelta(days=2)
    last = today + timedelta(days=330)  # Google n'affiche pas plus loin
    # destinations : liste explicite, sinon toutes celles des zones
    dests = lg.get("destinations") or [d for z in cfg.get("zones", []) for d in z["destinations"]]
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
                            for dest in dests:
                                trips.append(("long", o, dest, d, r))
            d += timedelta(days=pas)
    return trips


def combo_key(t):
    kind, o, dest, d, r = t
    return f"{kind[0]}|{o}|{dest}|{d:%y%m%d}|{r:%y%m%d}"


def pick(trips, n, vus, poids=None):
    """Prend les n combinaisons cherchées le moins récemment (jamais cherchées d'abord).
    Tout est donc couvert avant de refaire deux fois la même recherche.
    poids : part de chaque aéroport de départ (ex. {"AMS": 0.4} = cherché moins souvent)."""
    if n <= 0 or not trips:
        return []
    rnd = random.Random()

    def plus_anciennes_d_abord(lst):
        return sorted(lst, key=lambda t: (vus.get(combo_key(t), ""), rnd.random()))

    if not poids:
        return plus_anciennes_d_abord(trips)[:n]
    groupes = {}
    for t in trips:
        groupes.setdefault(t[1], []).append(t)
    total = sum(float(poids.get(o, 1)) for o in groupes)
    sel = []
    for o, g in groupes.items():
        quota = int(n * float(poids.get(o, 1)) / total)
        sel += plus_anciennes_d_abord(g)[:quota]
    if len(sel) < n:   # arrondis, ou aéroport dont tout a déjà été pris : on complète
        pris = {combo_key(t) for t in sel}
        reste = plus_anciennes_d_abord([t for t in trips if combo_key(t) not in pris])
        sel += reste[:n - len(sel)]
    return sel[:n]


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


def detect_devise(raw):
    raw = str(raw)
    if "€" in raw or "EUR" in raw:
        return "EUR"
    if "£" in raw or "GBP" in raw:
        return "GBP"
    if "$" in raw or "USD" in raw:
        return "USD"
    return "EUR"


_TAUX = {}


def taux_vers_eur(code):
    """Taux de change du jour (gratuit, sans clé). Valeur de secours si indisponible."""
    if code == "EUR":
        return 1.0
    if code in _TAUX:
        return _TAUX[code]
    rate = None
    for url in (f"https://api.frankfurter.dev/v1/latest?base={code}&symbols=EUR",
                f"https://api.frankfurter.app/latest?from={code}&to=EUR"):
        try:
            rate = float(json.loads(urllib.request.urlopen(url, timeout=15).read())["rates"]["EUR"])
            break
        except Exception:
            continue
    if rate is None:
        rate = {"USD": 0.92, "GBP": 1.15}.get(code, 1.0)
        print(f"Taux de change indisponible : valeur approximative utilisée pour {code} ({rate})")
    else:
        print(f"Conversion {code} → EUR au taux de {rate:.4f}")
    _TAUX[code] = rate
    return rate


HORS_HORAIRE = "hors_horaire"   # des vols existent, mais aucun dans la fenêtre horaire voulue


def minutes_du_jour(texte):
    """'7:30 PM on Thu, Nov 26' -> 1170 ; '19:30' -> 1170 ; illisible -> None."""
    m = re.search(r"(\d{1,2}):(\d{2})\s*([AaPp][Mm])?", str(texte))
    if not m:
        return None
    h, mn, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap:
        h = h % 12 + (12 if ap.lower() == "pm" else 0)
    return h * 60 + mn


def fenetre_horaire(regle):
    """{'apres': '19:00'} ou {'avant': '12:00'} -> (minimum, maximum) en minutes, sinon None."""
    if not regle:
        return None
    lo = minutes_du_jour(regle["apres"]) if "apres" in regle else 0
    hi = minutes_du_jour(regle["avant"]) if "avant" in regle else 24 * 60
    return lo, hi


ILLISIBLES = []   # exemples d'horaires que le filtre n'a pas su lire (affichés dans le journal)


def dans_fenetre(depart, fenetre):
    if not fenetre:
        return True
    mn = minutes_du_jour(depart)
    if mn is None:      # horaire illisible : on ne rejette pas le vol
        if len(ILLISIBLES) < 3:
            ILLISIBLES.append(str(depart)[:40])
        return True
    return fenetre[0] <= mn <= fenetre[1]


def _resultat(flight_data, trip):
    from fast_flights import Passengers
    pax = Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0)
    try:
        # on demande directement les prix en euros à Google
        from fast_flights import create_filter, get_flights_from_filter
        flt = create_filter(flight_data=flight_data, trip=trip, seat="economy", passengers=pax)
        return get_flights_from_filter(flt, currency="EUR", mode="fallback")
    except (ImportError, TypeError):
        from fast_flights import get_flights
        return get_flights(flight_data=flight_data, trip=trip, seat="economy",
                           passengers=pax, fetch_mode="fallback")


def _candidats(result, directs, fenetre):
    """Vols retenus (directs si demandé, dans la fenêtre horaire) avec leur prix en euros.
    Retourne (candidats, nombre_de_vols_directs, nombre_dans_la_fenetre)."""
    flights = list(result.flights)
    if directs:
        flights = [f for f in flights
                   if str(getattr(f, "stops", 0)).strip().lower() in ("0", "none", "nonstop")]
    n_directs = len(flights)
    flights = [f for f in flights if dans_fenetre(getattr(f, "departure", ""), fenetre)]
    cands = []
    for f in flights:
        p = parse_price(f.price)
        if p:
            # tout est converti en euros, quelle que soit la devise renvoyée par Google
            cands.append((round(p * taux_vers_eur(detect_devise(f.price))), f))
    return cands, n_directs, len(flights)


def _infos(vol):
    return {"compagnie": str(getattr(vol, "name", "") or ""),
            "depart": str(getattr(vol, "departure", "") or "")}


def search_price(origin, dest, d, r, directs=False, fenetre=None):
    """Retourne (prix_aller_retour_min_en_euros, avis_google, infos_du_vol), ou None s'il n'y a
    aucun vol, ou HORS_HORAIRE si des vols existent mais aucun dans la fenêtre horaire de l'aller."""
    from fast_flights import FlightData

    result = _resultat([
        FlightData(date=d.isoformat(), from_airport=origin, to_airport=dest),
        FlightData(date=r.isoformat(), from_airport=dest, to_airport=origin),
    ], "round-trip")
    cands, n_directs, n_fenetre = _candidats(result, directs, fenetre)
    if n_directs and not n_fenetre:
        return HORS_HORAIRE
    if not cands:
        return None
    prix, best = min(cands, key=lambda c: c[0])
    return prix, getattr(result, "current_price", None), _infos(best)


def search_retour(origin, dest, jour, directs=False, fenetre=None):
    """Vérifie le vol retour (dest -> origin) ce jour-là, en aller simple, dans la fenêtre horaire.
    Retourne (prix_aller_simple_en_euros, infos_du_vol) ou None."""
    from fast_flights import FlightData

    result = _resultat([FlightData(date=jour.isoformat(), from_airport=dest, to_airport=origin)],
                       "one-way")
    cands, _, _ = _candidats(result, directs, fenetre)
    if not cands:
        return None
    prix, best = min(cands, key=lambda c: c[0])
    return prix, _infos(best)


def verifier_retour(origin, dest, jour, directs, fenetre):
    """Statut du retour : ok (avec horaire et prix indicatif), aucun, ou inconnu."""
    try:
        res = search_retour(origin, dest, jour, directs, fenetre)
    except Exception as e:
        return {"statut": "aucun"} if est_vide(e) else {"statut": "inconnu"}
    if res is None:
        return {"statut": "aucun"}
    prix, info = res
    return {"statut": "ok", "prix": prix, **info}


def est_vide(exc):
    """Certaines erreurs veulent simplement dire 'aucun vol sur cette route'."""
    m = str(exc).lower()
    return any(s in m for s in ("no flights", "no result", "aucun vol"))


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
    section = cfg.get("week_end" if kind == "week_end" else "long_sejour", {})
    return section.get("prix_max_alerte", 0), "plafond par défaut"


def evaluate(cfg, kind, dest, price, google_opinion, history_prices, record=None):
    """Retourne (est_une_offre, raisons, prix_habituel).
    record = minimum déjà enregistré pour cette route : {"p": prix_min, "n": nb_de_relevés}."""
    det = cfg["detection"]
    seuil_abs, zone = plafond(cfg, kind, dest)
    raisons, median = [], None
    if det.get("baisse_vs_historique", True) and len(history_prices) >= det["echantillon_minimum"]:
        median = statistics.median(history_prices)
        if price <= median * (1 - det["reduction_minimum"] / 100):
            pct = round((1 - price / median) * 100)
            raisons.append(f"{pct}% sous le prix habituel (~{round(median)} €)")
    # Record : le meilleur prix jamais relevé sur cette route depuis le début
    rec = det.get("record_prix") or {}
    if rec.get("actif") and record and record["n"] >= rec.get("echantillon_minimum", 15):
        garde_fou = seuil_abs * rec.get("garde_fou_x_plafond", 1.5) if seuil_abs else None
        if garde_fou is None or price <= garde_fou:   # évite un "record" qui reste un prix élevé
            if price < record["p"]:
                raisons.append(f"🏆 nouveau record : {price} € (ancien minimum {record['p']} €)")
            elif price == record["p"]:
                raisons.append(f"🏆 égale le meilleur prix enregistré ({record['p']} €)")
            elif price <= record["p"] + rec.get("marge_euros", 5):
                raisons.append(f"🏆 à {price - record['p']} € du meilleur prix enregistré ({record['p']} €)")
    if seuil_abs and price <= seuil_abs:
        raisons.append(f"sous ton plafond de {seuil_abs} € ({zone})")
    if det.get("utiliser_avis_google") and google_opinion == "low" and median and price <= median * 0.85:
        raisons.append("Google indique un prix bas")
    return bool(raisons), "\n".join(raisons), median


# ---------------------------------------------------------------
#  4. Liens et notifications (ntfy gratuit, mail en option)
# ---------------------------------------------------------------
def _varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _champ(num, payload):
    return _varint((num << 3) | 2) + _varint(len(payload)) + payload


def _aeroport(code):
    return bytes([0x08, 0x01]) + _champ(2, code.encode())


def _vol(jour, depart, arrivee, directs=False):
    escales = bytes([0x28, 0x00]) if directs else b""   # 0 escale
    return (_champ(2, jour.encode()) + escales
            + _champ(13, _aeroport(depart)) + _champ(14, _aeroport(arrivee)))


def lien_vol(origin, dest, d, r, directs=False):
    """Lien Google Flights qui ouvre directement la liste des vols aller-retour
    pour ces aéroports et ces dates, en euros (vols directs seulement si demandé)."""
    b = bytes([0x08, 0x1C, 0x10, 0x02])
    b += _champ(3, _vol(d.isoformat(), origin, dest, directs))
    b += _champ(3, _vol(r.isoformat(), dest, origin, directs))
    b += bytes([0x40, 0x01, 0x48, 0x01, 0x70, 0x01])
    b += _champ(16, bytes([0x08]) + b"\xff" * 9 + b"\x01") + bytes([0x98, 0x01, 0x01])
    tfs = base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    return f"https://www.google.com/travel/flights/search?tfs={tfs}&hl=fr&curr=EUR"


def lien_recherche(origin, dest, d, r):
    """Lien de secours (recherche en langage naturel)."""
    q = f"Flights from {origin} to {dest} on {d} through {r}"
    return "https://www.google.com/travel/flights?hl=fr&curr=EUR&q=" + urllib.parse.quote(q)


def notify_ntfy(topic, title, message, click=None, secours=None):
    payload = {"topic": topic, "title": title, "message": message, "tags": ["airplane"]}
    if click:
        payload["click"] = click
    if secours:
        payload["actions"] = [{"action": "view", "label": "Lien de secours", "url": secours}]
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
        title = f"{nom(dl['origin'])} ⇄ {nom(dl['dest'])} : {dl['price']} € A/R"
        nuits = (dl["r"] - dl["d"]).days
        type_ = "week-end" if dl["kind"] == "week_end" else "long séjour"
        msg = (f"💶 {dl['price']} € l'aller-retour\n"
               f"{jour_fr(dl['d'])} → {jour_fr(dl['r'])} · {nuits} nuits ({type_})\n"
               f"{dl['why']}")
        vol = " · ".join(x for x in (dl["info"].get("compagnie"), dl["info"].get("depart")) if x)
        if vol:
            msg += f"\n✈️ Aller : {vol}"
        rt = dl.get("retour")
        if rt:
            if rt["statut"] == "ok":
                msg += (f"\n🛬 Retour : {rt.get('depart', '')} · {rt.get('compagnie', '')}"
                        f" · ~{rt['prix']} € l'aller simple (indicatif)")
            elif rt["statut"] == "aucun":
                msg += "\n⚠️ Pas de retour direct trouvé à l'horaire voulu : vérifie avant de réserver"
            else:
                msg += "\n⚠️ Retour non vérifié : vérifie l'horaire avant de réserver"
        lines.append(f"{title}\n{msg}\n{dl['link']}\n(secours : {dl['link2']})\n")
        if topic:
            try:
                notify_ntfy(topic, title, msg, dl["link"], dl["link2"])
            except Exception as e:  # une notif ratée ne doit pas tout casser
                print("ntfy erreur:", e)
    if deals:
        notify_mail(f"✈️ {len(deals)} bonne(s) offre(s) de vol", "\n".join(lines))


# ---------------------------------------------------------------
#  5. Programme principal
# ---------------------------------------------------------------
def pause(lim):
    p = lim["pause_secondes"]
    time.sleep(random.uniform(p[0], p[1]) if isinstance(p, (list, tuple)) else p)


def main(config_path, data_dir):
    config_path, data_dir = Path(config_path), Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    history_file = data_dir / "history.json"    # prix relevés par route
    notified_file = data_dir / "notified.json"  # offres déjà signalées
    vus_file = data_dir / "vus.json"            # dernière recherche de chaque combinaison

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if "zones" not in cfg:
        cfg["zones"] = yaml.safe_load((ROOT / "zones.yaml").read_text(encoding="utf-8"))["zones"]
    today = date.today()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
    history = load_json(history_file, {})
    notified = load_json(notified_file, {})
    vus = load_json(vus_file, {})
    lim = cfg["limites"]
    vides = history.setdefault("_vides", {})
    minimums = history.setdefault("_min", {})   # meilleur prix relevé par route depuis le début

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
    if wk and lg:
        n_wk = int(lim["recherches_max"] * lim.get("part_week_end", 0.7))
    else:
        n_wk = lim["recherches_max"] if wk else 0
    poids = cfg.get("poids_aeroports")
    trips = pick(wk, n_wk, vus, poids) + pick(lg, lim["recherches_max"] - n_wk, vus, poids)
    random.shuffle(trips)
    print(f"{len(trips)} recherches prévues ({len(wk)} week-end et {len(lg)} longs séjours possibles)")

    sans_zone = sorted({t[2] for t in wk + lg
                        if not any(t[2] in z["destinations"] for z in cfg.get("zones", []))})
    if sans_zone:
        print("Destinations sans zone de plafond (plafond par défaut utilisé):", ", ".join(sans_zone))

    t0 = time.time()
    deals, ok, fails, hors = [], 0, 0, 0
    empties, succeeded, recent_empty = [], set(), []
    consec_echecs, bloque = 0, False
    for t in trips:
        kind, o, dest, d, r = t
        if time.time() - t0 > lim["duree_max_minutes"] * 60:
            print("Durée maximale atteinte, arrêt propre.")
            break
        if o == dest:
            continue
        section = cfg["week_end" if kind == "week_end" else "long_sejour"]
        directs = bool(section.get("directs_seulement"))
        horaires = section.get("horaires") or {}
        fen = None
        if kind == "week_end":   # fenêtre horaire de l'aller (ex. jeudi soir tard, vendredi matin)
            fen = fenetre_horaire((horaires.get("depart") or {}).get(JOURS_NOMS[d.weekday()]))
        res, erreur = None, None
        try:
            res = search_price(o, dest, d, r, directs, fen)
        except Exception as e:
            if not est_vide(e):   # "aucun vol" n'est pas une vraie erreur
                erreur = e
        if erreur is not None:
            fails += 1
            consec_echecs += 1
            if fails <= 8:        # on n'affiche que les premières erreurs
                print(f"échec {o}-{dest} {d}: {str(erreur)[:100]}")
            if fails >= 15 and ok == 0:
                print("Trop d'échecs sans aucun succès : arrêt (Google a peut-être changé).")
                break
            maxi = lim.get("echecs_consecutifs_max", 10)
            if consec_echecs >= maxi:
                print(f"{maxi} échecs d'affilée : blocage probable, arrêt pour ne pas insister.")
                break
            if consec_echecs == max(3, maxi // 2):
                print(f"{consec_echecs} échecs d'affilée : pause de 2 minutes.")
                time.sleep(120)
            pause(lim)
            continue
        consec_echecs = 0
        pause(lim)
        key = route_key(kind, o, dest)
        vus[combo_key(t)] = now
        if res == HORS_HORAIRE:   # la route existe, simplement pas à l'horaire voulu ce jour-là
            hors += 1
            succeeded.add(key)
            vides.pop(key, None)
            recent_empty = []
            continue
        if not res:
            empties.append(key)
            recent_empty.append(combo_key(t))
            if len(recent_empty) >= 25:
                print("25 recherches vides d'affilée : Google ne renvoie plus rien, arrêt.")
                for ck in recent_empty:   # ces recherches ne comptent pas comme faites
                    vus.pop(ck, None)
                bloque = True
                break
            continue
        recent_empty = []
        ok += 1
        succeeded.add(key)
        vides.pop(key, None)
        price, opinion, info = res
        past = [h["p"] for h in history.get(key, [])]
        prev = dict(minimums[key]) if key in minimums else None   # minimum AVANT ce relevé
        good, why, median = evaluate(cfg, kind, dest, price, opinion, past, prev)
        m = minimums.setdefault(key, {"p": price, "n": 0, "d": today.isoformat(), "dep": d.isoformat()})
        m["n"] += 1
        if price < m["p"]:
            m.update(p=price, d=today.isoformat(), dep=d.isoformat())
        if cfg["detection"].get("baisse_vs_historique", True):   # inutile de garder les prix sinon
            history.setdefault(key, []).append({"p": price, "c": today.isoformat()})
            history[key] = history[key][-300:]
        if good:
            nkey = f"{key}|{d}|{r}"
            if nkey not in notified or price < notified[nkey]:
                retour = None
                if kind == "week_end":   # le retour est-il à l'horaire voulu (ex. dimanche soir) ?
                    regle = (horaires.get("retour") or {}).get(JOURS_NOMS[r.weekday()])
                    if regle:
                        retour = verifier_retour(o, dest, r, directs, fenetre_horaire(regle))
                        pause(lim)
                        if retour["statut"] == "aucun" and section.get("retour_strict"):
                            continue   # pas de retour au bon horaire : pas d'alerte
                notified[nkey] = price
                seuil = plafond(cfg, kind, dest)[0]
                score = (1 - price / median) if median else ((1 - price / seuil) if seuil else 0.2)
                if "🏆" in why:
                    score += 1.0   # les records passent en premier
                deals.append({"kind": kind, "origin": o, "dest": dest, "d": d, "r": r,
                              "price": price, "why": why, "score": score, "info": info,
                              "retour": retour,
                              "link": lien_vol(o, dest, d, r, directs),
                              "link2": lien_recherche(o, dest, d, r)})

    # Routes sans aucun vol : on ne les met de côté que si ce n'est pas un blocage de Google
    total = ok + len(empties)
    if bloque or (total >= 30 and len(empties) / total > 0.6):
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
    print(f"{ok} prix relevés, {hors} hors horaire, {len(empties)} sans résultat, {fails} échecs, "
          f"{len(deals)} offre(s) en {mins:.1f} min. {cadence}")
    if ILLISIBLES:
        print("Attention : horaires illisibles, le filtre horaire n'a pas agi sur ces vols. Exemples :",
              ILLISIBLES)
    mises_de_cote = sorted(
        f"{nom(k.split('|')[1])}→{nom(k.split('|')[2])}"
        for k, v in vides.items() if v["n"] >= lim["routes_vides_avant_pause"])
    print(f"Routes mises de côté ({len(mises_de_cote)}) : " + ", ".join(mises_de_cote))

    if deals:
        send_alerts(deals, cfg)
    elif os.environ.get("NTFY_TOPIC") and os.environ.get("NTFY_TEST") == "1":
        notify_ntfy(os.environ["NTFY_TOPIC"], "Test", f"Le détecteur fonctionne ({ok} prix relevés).")

    save_json(history_file, history)
    save_json(notified_file, notified)
    save_json(vus_file, vus)
    if ok == 0 and trips:
        sys.exit(1)  # fait apparaître l'échec dans GitHub
