"""Noms lisibles des aéroports pour les notifications.
Si tu ajoutes un code dans config.yaml, ajoute-le aussi ici (sinon le code s'affiche)."""

NOMS = {
    # Départs
    "LIL": "Lille", "CDG": "Paris (Roissy-CDG)", "ORY": "Paris (Orly)", "BVA": "Paris (Beauvais)",
    "BRU": "Bruxelles", "CRL": "Bruxelles (Charleroi)", "AMS": "Amsterdam",
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
}


def nom(code):
    return NOMS.get(code, code)
