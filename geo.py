"""Pays et continent de chaque destination (pour filtrer la page de recherche).
Si tu ajoutes une destination dans une config, ajoute aussi son code ici (sinon : « Autre »)."""

# continent -> pays -> codes des aéroports
GEO = {
    "Europe": {
        "Espagne": "BCN GRO MAD VLC ALC AGP SVQ GRX BIO SCQ PMI IBZ REU ZAZ VGO JRZ LEI TFS LPA ACE FUE TFN SPC",
        "Portugal": "LIS OPO FAO FNC PDL",
        "Italie": "FCO CIA MXP BGY VCE TSF VRN BLQ PSA NAP TRN BRI BDS CTA PMO CAG TRS FLR GOA",
        "Allemagne": "BER DUS CGN HAM MUC FRA NUE",
        "Autriche": "VIE SZG INN",
        "Suisse": "BSL",
        "Tchéquie": "PRG BRQ",
        "Hongrie": "BUD",
        "Pologne": "WAW KRK GDN WRO POZ KTW SZZ RZE",
        "Slovaquie": "BTS KSC",
        "Slovénie": "LJU",
        "Croatie": "ZAG SPU DBV",
        "Royaume-Uni": "STN LTN LGW MAN EDI BRS BHX LPL NCL GLA BFS LBA EMA CWL",
        "Irlande": "DUB ORK SNN",
        "France": "NCE",
        "Danemark": "CPH BLL",
        "Suède": "ARN NYO GOT MMX",
        "Norvège": "OSL TRF BGO TOS",
        "Finlande": "HEL RVN",
        "Pays baltes": "TLL RIX VNO KUN",
        "Islande": "KEF",
        "Grèce": "ATH SKG CFU RHO HER CHQ",
        "Chypre": "LCA PFO",
        "Malte": "MLA",
        "Balkans": "TIA SOF BEG SJJ SKP PRN TGD TIV",
        "Roumanie et Moldavie": "OTP CLJ TSR IAS SBZ KIV",
        "Turquie": "IST SAW",
    },
    "Afrique": {
        "Maroc": "RAK AGA FEZ TNG CMN OZZ ESU",
        "Tunisie": "TUN DJE MIR",
        "Algérie": "ALG ORN",
        "Égypte": "CAI HRG SSH RMF",
        "Cap-Vert": "SID BVC",
        "Afrique de l'Ouest": "DSS ABJ ACC DLA LOS",
        "Afrique de l'Est": "ADD DAR JRO ZNZ NBO",
        "Afrique australe": "CPT JNB",
        "Océan Indien": "TNR SEZ MRU RUN",
    },
    "Moyen-Orient et Caucase": {
        "Golfe et Oman": "DXB AUH DOH MCT",
        "Jordanie": "AQJ AMM",
        "Caucase": "TBS EVN GYD",
    },
    "Asie": {
        "Thaïlande": "BKK HKT CNX USM",
        "Vietnam": "SGN HAN DAD PQC",
        "Cambodge": "REP PNH",
        "Singapour et Malaisie": "SIN KUL",
        "Indonésie": "DPS CGK",
        "Philippines": "MNL CEB",
        "Japon": "TYO OSA",
        "Corée du Sud": "ICN",
        "Chine, Hong Kong, Taïwan": "PEK PVG HKG TPE",
        "Inde": "DEL BOM BLR MAA",
        "Sri Lanka, Maldives, Népal": "CMB MLE KTM",
        "Asie centrale": "TAS ALA",
    },
    "Amérique du Nord": {
        "États-Unis (est)": "JFK MIA BOS IAD PHL ORD ATL MCO DFW IAH",
        "États-Unis (ouest)": "LAX SFO SEA LAS DEN",
        "Canada": "YUL YYZ YQB YHZ YVR",
        "Mexique": "MEX CUN",
    },
    "Amérique centrale et Caraïbes": {
        "Antilles françaises": "PTP FDF SXM",
        "Caraïbes": "PUJ SDQ HAV SJU BGI MBJ NAS",
        "Amérique centrale": "PTY SJO GUA",
    },
    "Amérique du Sud": {
        "Brésil": "GRU GIG SSA REC FOR",
        "Argentine, Chili, Uruguay": "EZE SCL MVD",
        "Pérou, Colombie, Équateur": "LIM BOG CTG MDE UIO",
    },
    "Océanie et Pacifique": {
        "Australie": "SYD MEL BNE PER",
        "Nouvelle-Zélande": "AKL",
        "Pacifique": "NOU PPT HNL",
    },
}

CODE_VERS_GEO = {code: (continent, pays)
                 for continent, pays_d in GEO.items()
                 for pays, codes in pays_d.items() for code in codes.split()}


def geo(code):
    """(continent, pays) d'un aéroport ; ('Autre', 'Autre') s'il est inconnu."""
    return CODE_VERS_GEO.get(code, ("Autre", "Autre"))
