"""Noms lisibles des aéroports pour les notifications.
Si tu ajoutes un code dans config.yaml, ajoute-le aussi ici (sinon le code s'affiche)."""

NOMS = {
    # Départs
    "LIL": "Lille", "CDG": "Paris (Roissy-CDG)", "ORY": "Paris (Orly)", "BVA": "Paris (Beauvais)",
    "BRU": "Bruxelles (Zaventem)", "CRL": "Bruxelles (Charleroi)", "AMS": "Amsterdam",
    # Europe
    "BCN": "Barcelone", "MAD": "Madrid", "LIS": "Lisbonne", "OPO": "Porto", "FCO": "Rome",
    "MXP": "Milan", "VCE": "Venise", "NAP": "Naples", "ATH": "Athènes", "PRG": "Prague",
    "BUD": "Budapest", "VIE": "Vienne", "BER": "Berlin", "WAW": "Varsovie", "KRK": "Cracovie",
    "DUB": "Dublin", "EDI": "Édimbourg", "LON": "Londres", "MLA": "Malte", "PMI": "Palma de Majorque",
    "AGP": "Malaga", "SVQ": "Séville", "VLC": "Valence", "NCE": "Nice", "CPH": "Copenhague",
    "ARN": "Stockholm", "OSL": "Oslo", "ZAG": "Zagreb", "TIA": "Tirana",
    # Monde
    "JFK": "New York", "YUL": "Montréal", "MIA": "Miami", "LAX": "Los Angeles", "MEX": "Mexico",
    "CUN": "Cancún", "BKK": "Bangkok", "SGN": "Hô Chi Minh-Ville", "HAN": "Hanoï", "SIN": "Singapour",
    "KUL": "Kuala Lumpur", "DPS": "Bali", "TYO": "Tokyo", "ICN": "Séoul", "DXB": "Dubaï",
    "DOH": "Doha", "CMN": "Casablanca", "RAK": "Marrakech", "TUN": "Tunis", "CAI": "Le Caire",
    "DEL": "Delhi", "BOM": "Mumbai", "CPT": "Le Cap", "NBO": "Nairobi", "ZNZ": "Zanzibar",
    "MRU": "Île Maurice", "RUN": "La Réunion", "PTP": "Guadeloupe", "FDF": "Martinique",
    "PUJ": "Punta Cana", "HAV": "La Havane", "GRU": "São Paulo", "EZE": "Buenos Aires",
    "LIM": "Lima", "BOG": "Bogotá", "PPT": "Tahiti",
    # Ajouts court courrier
    "GRO": "Gérone", "ALC": "Alicante", "GRX": "Grenade", "BIO": "Bilbao",
    "SCQ": "Saint-Jacques-de-Compostelle", "IBZ": "Ibiza", "FAO": "Faro", "TFS": "Tenerife",
    "LPA": "Grande Canarie", "ACE": "Lanzarote", "FUE": "Fuerteventura", "FNC": "Madère",
    "CIA": "Rome (Ciampino)", "BGY": "Milan (Bergame)", "TSF": "Venise (Trévise)", "VRN": "Vérone",
    "BLQ": "Bologne", "PSA": "Pise", "BRI": "Bari", "BDS": "Brindisi", "CTA": "Catane",
    "PMO": "Palerme", "CAG": "Cagliari", "TRN": "Turin",
    "GDN": "Gdansk", "WRO": "Wrocław", "POZ": "Poznań", "KTW": "Katowice", "BTS": "Bratislava",
    "LJU": "Ljubljana", "SPU": "Split", "DBV": "Dubrovnik", "SOF": "Sofia", "OTP": "Bucarest",
    "BEG": "Belgrade", "SJJ": "Sarajevo", "SKP": "Skopje", "TLL": "Tallinn", "RIX": "Riga",
    "VNO": "Vilnius", "HEL": "Helsinki", "KEF": "Reykjavik",
    "STN": "Londres (Stansted)", "LTN": "Londres (Luton)", "LGW": "Londres (Gatwick)",
    "MAN": "Manchester", "ORK": "Cork", "BRS": "Bristol",
    "SKG": "Thessalonique", "CFU": "Corfou", "RHO": "Rhodes", "HER": "Héraklion (Crète)",
    "CHQ": "La Canée (Crète)", "LCA": "Larnaca (Chypre)", "PFO": "Paphos (Chypre)",
    "IST": "Istanbul", "SAW": "Istanbul (Sabiha Gökçen)",
    "AGA": "Agadir", "FEZ": "Fès", "TNG": "Tanger", "DJE": "Djerba", "MIR": "Monastir",
}


def nom(code):
    return NOMS.get(code, code)
