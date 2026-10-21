"""Coûts annexes ESTIMÉS : transfert aéroport → centre-ville (court courrier) et hôtel.

⚠️ Ce sont des ESTIMATIONS arrondies (pas des prix en direct, il n'existe pas de source gratuite
fiable pour ça). Elles servent à comparer des offres entre elles, pas à budgéter au centime.
Les tarifs de transport changent peu (1 à 2 fois par an) : vérifie sur le site de l'opérateur
avant de réserver, et corrige ici les chiffres que tu constates.

TRANSFERT : code aéroport -> (moyen de transport, prix aller-retour en € pour 1 personne)
HOTEL     : code aéroport -> prix d'une nuit PAR PERSONNE, en chambre double d'hôtel/auberge
            simple (donc la moitié de la chambre), hors saison haute.
"""

ESTIMATION = "estimation 2026, à vérifier"

TRANSFERT = {
    # Espagne, Portugal, îles
    "BCN": ("Aerobus", 12.5), "GRO": ("bus", 6), "MAD": ("bus Express / métro", 10), "VLC": ("métro", 10),
    "ALC": ("bus", 8), "AGP": ("train", 4), "SVQ": ("bus", 8), "GRX": ("bus", 6), "BIO": ("bus", 6),
    "SCQ": ("bus", 6), "PMI": ("bus", 10), "IBZ": ("bus", 8), "REU": ("bus vers Barcelone", 20),
    "ZAZ": ("bus", 8), "VGO": ("bus", 4), "JRZ": ("taxi", 30), "LEI": ("bus", 5),
    "LIS": ("métro", 4), "OPO": ("métro", 6), "FAO": ("bus", 5),
    "TFS": ("bus", 8), "TFN": ("bus", 9), "LPA": ("bus", 7), "ACE": ("bus", 6), "FUE": ("bus", 8),
    "FNC": ("bus", 16), "PDL": ("bus", 4), "SPC": ("bus", 8),
    # Italie
    "FCO": ("bus Terravision", 12), "CIA": ("bus", 12), "MXP": ("navette / train", 20),
    "BGY": ("navette", 10), "VCE": ("bus", 10), "TSF": ("bus", 12), "VRN": ("bus", 12),
    "BLQ": ("Aerobus", 12), "PSA": ("navette PisaMover", 6), "NAP": ("bus Alibus", 10),
    "TRN": ("bus", 15), "BRI": ("bus", 10), "BDS": ("bus", 6), "CTA": ("bus Alibus", 8),
    "PMO": ("bus", 12), "CAG": ("bus", 6), "TRS": ("bus", 10), "FLR": ("tram / bus", 10),
    "GOA": ("bus Volabus", 8),
    # Europe centrale et de l'est
    "BER": ("train S-Bahn", 9), "VIE": ("train S-Bahn", 9), "PRG": ("bus + métro", 3),
    "BUD": ("bus + métro", 4), "WAW": ("train", 3), "KRK": ("train", 8), "GDN": ("bus / tram", 3),
    "WRO": ("bus", 3), "POZ": ("bus", 4), "KTW": ("train", 8), "BTS": ("bus", 3),
    "LJU": ("bus", 8), "ZAG": ("bus", 16), "SZZ": ("bus", 3), "RZE": ("bus", 3),
    "BRQ": ("bus", 4), "KSC": ("bus", 3), "CLJ": ("bus", 3), "TSR": ("bus", 3), "IAS": ("bus", 3),
    "SBZ": ("bus", 3), "OTP": ("bus / train", 3), "SOF": ("métro", 2), "BEG": ("bus", 7),
    "SJJ": ("taxi", 12), "SKP": ("navette", 8), "TIA": ("bus", 6), "PRN": ("bus", 4),
    "TGD": ("taxi", 12), "TIV": ("taxi", 25), "KIV": ("bus", 5), "KUN": ("bus", 5),
    "SPU": ("navette", 8), "DBV": ("navette", 20),
    # Allemagne, Autriche, Suisse
    "DUS": ("S-Bahn", 8), "CGN": ("S-Bahn", 6), "HAM": ("S-Bahn", 8), "MUC": ("S-Bahn", 27),
    "FRA": ("S-Bahn", 10), "NUE": ("métro", 6), "BSL": ("bus", 8), "SZG": ("bus", 6), "INN": ("bus", 5),
    # Royaume-Uni et Irlande
    "STN": ("bus / train", 25), "LTN": ("bus / train", 25), "LGW": ("train", 28), "MAN": ("train / tram", 12),
    "EDI": ("tram", 12), "DUB": ("bus", 12), "ORK": ("bus", 12), "BRS": ("bus", 14), "BHX": ("train", 7),
    "LPL": ("bus", 6), "NCL": ("métro", 10), "GLA": ("bus", 11), "BFS": ("bus", 13), "LBA": ("bus", 10),
    "EMA": ("bus", 10), "CWL": ("bus", 12), "SNN": ("bus", 16), "NCE": ("tram", 3),
    # Nord
    "CPH": ("métro", 9), "OSL": ("train Flytoget / bus", 35), "ARN": ("bus Flygbussarna", 24),
    "HEL": ("train", 9), "TLL": ("tram", 4), "RIX": ("bus", 4), "VNO": ("train", 3),
    "KEF": ("bus Flybus", 55), "BLL": ("bus", 10), "GOT": ("bus", 22), "MMX": ("bus", 30),
    "NYO": ("bus", 30), "TRF": ("bus", 40), "BGO": ("tramway", 8), "TOS": ("bus", 20), "RVN": ("bus", 14),
    # Grèce, Chypre, Malte, Turquie
    "ATH": ("métro", 16), "SKG": ("bus", 4), "CFU": ("bus", 4), "RHO": ("bus", 6), "HER": ("bus", 4),
    "CHQ": ("bus", 6), "MLA": ("bus", 4), "LCA": ("bus", 8), "PFO": ("bus", 8),
    "IST": ("bus Havaist", 10), "SAW": ("bus Havabus", 8),
    # Maghreb, Égypte, Cap-Vert, Jordanie
    "RAK": ("bus", 6), "AGA": ("bus / taxi", 8), "FEZ": ("bus", 8), "TNG": ("taxi", 30), "CMN": ("train", 12),
    "TUN": ("bus", 3), "DJE": ("taxi", 24), "MIR": ("taxi", 24), "OZZ": ("taxi", 12), "ESU": ("taxi", 20),
    "HRG": ("taxi", 16), "SSH": ("taxi", 16), "RMF": ("taxi / navette hôtel", 70),
    "SID": ("taxi", 40), "BVC": ("taxi", 30), "AQJ": ("taxi", 12),
}

HOTEL = {
    # --- Espagne, Portugal, îles ---
    "BCN": 45, "GRO": 32, "MAD": 38, "VLC": 32, "ALC": 30, "AGP": 33, "SVQ": 33, "GRX": 28, "BIO": 36,
    "SCQ": 28, "PMI": 38, "IBZ": 45, "REU": 30, "ZAZ": 28, "VGO": 28, "JRZ": 30, "LEI": 26,
    "LIS": 40, "OPO": 33, "FAO": 33, "TFS": 35, "TFN": 33, "LPA": 32, "ACE": 33, "FUE": 33, "FNC": 40,
    "PDL": 38, "SPC": 33,
    # --- Italie ---
    "FCO": 45, "CIA": 45, "MXP": 48, "BGY": 40, "VCE": 55, "TSF": 40, "VRN": 40, "BLQ": 38, "PSA": 35,
    "NAP": 33, "TRN": 38, "BRI": 30, "BDS": 30, "CTA": 30, "PMO": 30, "CAG": 33, "TRS": 38, "FLR": 48,
    "GOA": 36,
    # --- Europe centrale et de l'est ---
    "BER": 38, "VIE": 42, "PRG": 30, "BUD": 28, "WAW": 28, "KRK": 25, "GDN": 28, "WRO": 25, "POZ": 25,
    "KTW": 22, "BTS": 28, "LJU": 38, "ZAG": 30, "SZZ": 22, "RZE": 20, "BRQ": 26, "KSC": 20,
    "CLJ": 25, "TSR": 22, "IAS": 20, "SBZ": 24, "OTP": 25, "SOF": 20, "BEG": 22, "SJJ": 22, "SKP": 20,
    "TIA": 22, "PRN": 20, "TGD": 25, "TIV": 30, "KIV": 20, "KUN": 22, "SPU": 38, "DBV": 55,
    "KEF": 70,
    # --- Allemagne, Autriche, Suisse ---
    "DUS": 40, "CGN": 38, "HAM": 40, "MUC": 50, "FRA": 45, "NUE": 35, "BSL": 55, "SZG": 45, "INN": 45,
    # --- Royaume-Uni et Irlande ---
    "STN": 50, "LTN": 50, "LGW": 50, "LON": 55, "MAN": 38, "EDI": 55, "DUB": 55, "ORK": 45, "BRS": 42,
    "BHX": 38, "LPL": 36, "NCL": 36, "GLA": 38, "BFS": 38, "LBA": 36, "EMA": 36, "CWL": 38, "SNN": 40,
    "NCE": 50,
    # --- Nord ---
    "CPH": 60, "OSL": 65, "ARN": 55, "HEL": 50, "TLL": 32, "RIX": 30, "VNO": 28, "BLL": 45, "GOT": 45,
    "MMX": 45, "NYO": 55, "TRF": 60, "BGO": 58, "TOS": 65, "RVN": 65,
    # --- Grèce, Chypre, Malte, Turquie ---
    "ATH": 32, "SKG": 28, "CFU": 35, "RHO": 33, "HER": 30, "CHQ": 30, "MLA": 38, "LCA": 38, "PFO": 38,
    "IST": 30, "SAW": 30,
    # --- Maghreb, Égypte, Proche-Orient, Cap-Vert ---
    "RAK": 22, "AGA": 25, "FEZ": 18, "TNG": 22, "CMN": 28, "TUN": 20, "DJE": 22, "MIR": 22, "OZZ": 18,
    "ESU": 22, "ALG": 22, "ORN": 20, "HRG": 20, "SSH": 20, "RMF": 25, "SID": 38, "BVC": 38, "AQJ": 30,
    "CAI": 18, "AMM": 30, "TBS": 22, "EVN": 22, "GYD": 30,
    "DXB": 50, "DOH": 55, "AUH": 50, "MCT": 40,
    # --- Afrique, océan Indien ---
    "DSS": 30, "ABJ": 35, "ACC": 35, "DLA": 35, "LOS": 45, "ADD": 30, "DAR": 30, "JRO": 40, "NBO": 30,
    "ZNZ": 32, "JNB": 35, "CPT": 32, "TNR": 20, "SEZ": 70, "MRU": 45, "RUN": 40,
    # --- Amérique du Nord ---
    "JFK": 100, "YUL": 60, "MIA": 80, "BOS": 95, "IAD": 80, "PHL": 70, "YYZ": 65, "YQB": 55, "YHZ": 55,
    "ORD": 80, "ATL": 65, "MCO": 60, "DFW": 60, "IAH": 60, "DEN": 70, "LAS": 60, "SFO": 100,
    "SEA": 80, "YVR": 70, "LAX": 85,
    # --- Amérique centrale, Caraïbes, Amérique du Sud ---
    "MEX": 28, "CUN": 50, "PTP": 45, "FDF": 45, "PUJ": 50, "HAV": 40, "SJU": 70, "BGI": 90,
    "MBJ": 70, "NAS": 95, "SXM": 80, "SDQ": 40, "CTG": 38, "MDE": 28, "PTY": 45, "SJO": 40, "GUA": 30,
    "GRU": 28, "GIG": 30, "SSA": 25, "REC": 25, "FOR": 25, "EZE": 25, "SCL": 35, "MVD": 32, "LIM": 25,
    "BOG": 25, "UIO": 25,
    # --- Asie ---
    "BKK": 20, "SGN": 15, "HAN": 15, "SIN": 50, "KUL": 22, "DPS": 20, "TYO": 45, "ICN": 38, "DEL": 18,
    "BOM": 25, "MNL": 22, "CEB": 22, "HKG": 55, "TPE": 35, "PEK": 30, "PVG": 35, "OSA": 40, "CGK": 22,
    "HKT": 22, "CNX": 15, "REP": 15, "PNH": 15, "USM": 25, "DAD": 18, "PQC": 25, "BLR": 22, "MAA": 20,
    "CMB": 22, "MLE": 80, "KTM": 15, "TAS": 20, "ALA": 25,
    # --- Océanie et Pacifique ---
    "SYD": 65, "MEL": 60, "BNE": 60, "PER": 60, "AKL": 60, "NOU": 65, "HNL": 90, "PPT": 80,
}

# Multiplicateur de saison selon le mois du séjour (1.0 = prix de base).
# Valeurs volontairement simples : été et fêtes de fin d'année plus chers, novembre/janvier moins.
SAISON = {1: 0.9, 2: 0.95, 3: 1.0, 4: 1.1, 5: 1.05, 6: 1.1, 7: 1.25, 8: 1.3,
          9: 1.05, 10: 1.0, 11: 0.9, 12: 1.15}


def hotel_nuit(dest, mois=None):
    """Prix estimé d'une nuit par personne à destination (None si inconnu)."""
    base = HOTEL.get(dest)
    if base is None:
        return None
    return round(base * SAISON.get(mois, 1.0))


def ligne_transfert(dest):
    """Ligne pour la notification, ex. '🚆 Sur place : Aerobus ≈ 13 € A/R (estimation 2026, à vérifier)'."""
    t = TRANSFERT.get(dest)
    if not t:
        return ""
    moyen, prix = t
    p = f"{prix:g}".replace(".", ",")
    return f"🚆 Sur place : {moyen} ≈ {p} € A/R ({ESTIMATION})"
