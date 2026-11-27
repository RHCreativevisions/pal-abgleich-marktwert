"""Amtliche Marktdaten für den Pal-Abgleich.

Quelle: Immobilienmarktbericht Berlin 2025/2026, Gutachterausschuss für Grundstückswerte
in Berlin (Stand 31.07.2026, Berichtsjahr 2025, Lizenz dl-de/zero-2-0).
PDF: https://www.berlin.de/gutachterausschuss/_assets/amarktinformationen/amarktanalyse/04-03-010-2500.pdf

Segmentwerte in €/m² WERTRELEVANTE GESCHOSSFLÄCHE (WGF). Umrechnung Wohnfläche/WGF
im Mittel 81/100 (Bericht S. 49).
Tupel: (anzahl, grund_von, grund_bis, grund_mittel, wgf_von, wgf_bis, wgf_mittel,
        preis_von, preis_bis, preis_mittel)
"""

QUELLE = "Immobilienmarktbericht Berlin 2025/2026, Gutachterausschuss für Grundstückswerte in Berlin"
QUELLE_KURZ = "Gutachterausschuss Berlin, Marktbericht 2025/26"
UMRECHNUNG_WF_WGF = 0.81  # S. 49

BAUJAHRSGRUPPEN = [
    ("bis1919", None, 1919, "bis 1919"),
    ("1920-1948", 1920, 1948, "1920 bis 1948"),
    ("1949-1970", 1949, 1970, "1949 bis 1970"),
    ("1971-1990", 1971, 1990, "1971 bis 1990"),
    ("1991-2021", 1991, 2021, "1991 bis 2021"),
    ("ab2022", 2022, None, "ab 2022"),
]

# S. 52/53
FREISTEHEND = {
    "bis1919":   {"em": (5, 666, 1130, 807, 192, 419, 283, 2360, 4025, 3059),
                  "gut": (6, 669, 1232, 924, 104, 339, 214, 3990, 18889, 6934),
                  "ges": (10, 666, 1130, 835, 104, 339, 228, 2360, 5560, 3801)},
    "1920-1948": {"em": (209, 450, 962, 691, 92, 224, 154, 1688, 4744, 3175),
                  "gut": (48, 475, 1140, 806, 87, 334, 206, 2500, 7356, 4583),
                  "ges": (260, 439, 996, 700, 84, 250, 160, 1716, 5099, 3318)},
    "1949-1970": {"em": (123, 438, 947, 676, 78, 210, 139, 1852, 5256, 3486),
                  "gut": (28, 542, 1278, 903, 84, 284, 181, 2256, 6646, 4465),
                  "ges": (149, 438, 989, 700, 75, 227, 143, 1772, 5618, 3664)},
    "1971-1990": {"em": (152, 400, 852, 590, 93, 246, 165, 2262, 4371, 3279),
                  "gut": (23, 400, 1075, 684, 83, 258, 173, 2475, 5238, 3790),
                  "ges": (174, 400, 874, 594, 93, 250, 166, 2183, 4602, 3351)},
    "1991-2021": {"em": (172, 400, 836, 569, 109, 222, 165, 3030, 5195, 4085),
                  "gut": (14, 427, 888, 573, 123, 249, 174, 2794, 5000, 4026),
                  "ges": (184, 400, 842, 572, 109, 226, 164, 3030, 5195, 4094)},
    "ab2022":    {"em": (10, 401, 798, 523, 156, 208, 192, 2089, 4513, 3647),
                  "gut": None,
                  "ges": (11, 401, 798, 514, 142, 208, 187, 2089, 4718, 3754)},
}

# S. 54/55
DOPPELHAUS = {
    "bis1919":   {"em": (11, 295, 573, 428, 97, 331, 204, 1360, 4033, 2526), "gut": None,
                  "ges": (10, 295, 573, 428, 97, 239, 180, 1360, 4536, 2727)},
    "1920-1948": {"em": (51, 358, 658, 516, 88, 160, 120, 2151, 5078, 3628),
                  "gut": (6, 451, 638, 547, 104, 398, 218, 3846, 5952, 4614),
                  "ges": (59, 358, 658, 519, 73, 180, 124, 2265, 5078, 3711)},
    "1949-1970": {"em": (24, 291, 599, 425, 97, 154, 126, 1984, 4710, 3304),
                  "gut": (7, 215, 500, 399, 116, 365, 197, 3017, 10366, 5424),
                  "ges": (31, 291, 535, 426, 78, 185, 126, 1622, 5455, 3444)},
    "1971-1990": {"em": (45, 226, 431, 323, 94, 162, 124, 2410, 4468, 3523),
                  "gut": (9, 289, 590, 428, 107, 155, 128, 2392, 5038, 3703),
                  "ges": (54, 226, 465, 335, 94, 162, 124, 2205, 4468, 3448)},
    "1991-2021": {"em": (38, 236, 470, 345, 119, 182, 150, 2685, 5000, 3825),
                  "gut": (5, 321, 500, 379, 119, 220, 174, 3931, 8678, 6060),
                  "ges": (44, 240, 470, 348, 119, 186, 153, 2685, 5177, 3901)},
    "ab2022":    {"em": (12, 207, 467, 312, 84, 189, 144, 3163, 6417, 4393), "gut": None,
                  "ges": (12, 207, 467, 312, 84, 189, 144, 3163, 6417, 4393)},
}

# S. 56/57
REIHENHAUS = {
    "bis1919":   {"em": None, "gut": None, "ges": None},
    "1920-1948": {"em": (45, 129, 413, 253, 79, 150, 114, 1869, 5725, 3736),
                  "gut": (11, 170, 552, 288, 104, 180, 147, 4819, 6571, 5959),
                  "ges": (54, 129, 413, 251, 79, 165, 118, 2137, 6507, 4293)},
    "1949-1970": {"em": (66, 129, 436, 259, 92, 146, 114, 2232, 4543, 3308),
                  "gut": (10, 231, 567, 362, 102, 143, 117, 3025, 5487, 4164),
                  "ges": (76, 129, 449, 268, 92, 146, 115, 2232, 4554, 3354)},
    "1971-1990": {"em": (33, 181, 399, 286, 102, 183, 132, 2406, 4095, 3260),
                  "gut": (9, 200, 659, 317, 113, 177, 144, 2277, 5254, 3796),
                  "ges": (40, 181, 399, 284, 102, 179, 132, 2277, 4194, 3246)},
    "1991-2021": {"em": (60, 130, 381, 243, 123, 198, 159, 2583, 4801, 3581), "gut": None,
                  "ges": (61, 130, 381, 245, 123, 198, 160, 2583, 4801, 3581)},
    "ab2022":    {"em": (10, 222, 235, 227, 125, 240, 211, 3313, 4166, 3742), "gut": None,
                  "ges": (10, 222, 235, 227, 125, 240, 211, 3313, 4166, 3742)},
}

HAUSTYPEN = {
    "freistehend": {"name": "Freistehendes Ein-/Zweifamilienhaus", "plural": "freistehende Ein- und Zweifamilienhäuser",
                    "titel": "Freistehende Ein- und Zweifamilienhäuser", "dativ": "freistehenden Ein- und Zweifamilienhäuser", "kurz": "freistehend",
                    "tabelle": FREISTEHEND, "seiten": "S. 52–53", "mittel_kaufpreis": 670000,
                    "typische": {"vor1949": (400000, 850000), "1949-1989": (430000, 700000), "ab1990": (590000, 930000)},
                    "typ_seite": "S. 52"},
    "doppelhaus": {"name": "Doppelhaushälfte", "plural": "Doppelhaushälften",
                   "titel": "Doppelhaushälften", "dativ": "Doppelhaushälften", "kurz": "Doppelhaushälfte",
                   "tabelle": DOPPELHAUS, "seiten": "S. 54–55", "mittel_kaufpreis": 551000,
                   "typische": {"vor1949": (370000, 830000), "1949-1989": (350000, 610000), "ab1990": (475000, 780000)},
                   "typ_seite": "S. 54"},
    "reihenhaus": {"name": "Reihenhaus", "plural": "Reihenhäuser",
                   "titel": "Reihenhäuser", "dativ": "Reihenhäuser", "kurz": "Reihenhaus",
                   "tabelle": REIHENHAUS, "seiten": "S. 56–57", "mittel_kaufpreis": 542000,
                   "typische": {"vor1949": (375000, 965000), "1949-1989": (325000, 530000), "ab1990": (455000, 710000)},
                   "typ_seite": "S. 56"},
}

# S. 50, €/m² WOHNFLÄCHE, Ein- und Zweifamilienhäuser 2025: (anzahl, von, bis, mittel, mittel_2024)
ALTBEZIRK_HAUS = {
    "Wedding": (3, 3418, 6098, 5016, 4544), "Weißensee": (44, 2870, 6098, 4497, 4287),
    "Pankow": (53, 2700, 6520, 4723, 4871), "Charlottenburg": (16, 4689, 8841, 6273, 6838),
    "Wilmersdorf": (13, 5983, 10583, 8073, 8789), "Grunewald": (8, 4446, 20326, 9650, 12120),
    "Schmargendorf": (6, 6098, 8826, 7543, 7901), "Spandau": (169, 2413, 5956, 4133, 3994),
    "Steglitz": (87, 3078, 7104, 5037, 5313), "Zehlendorf": (54, 4129, 9417, 6487, 5551),
    "Dahlem": (7, 5302, 15635, 9120, 8645), "Tempelhof": (104, 2841, 5543, 4224, 4188),
    "Neukölln": (187, 2683, 5768, 4223, 3934), "Treptow": (74, 2977, 5333, 4253, 4317),
    "Köpenick": (44, 2856, 6002, 4496, 4314), "Marzahn": (67, 2956, 6137, 4312, 4101),
    "Hellersdorf": (113, 2790, 6017, 4461, 4042), "Lichtenberg": (28, 2924, 6695, 5062, 5380),
    "Hohenschönhausen": (35, 2623, 6554, 4659, 4323), "Reinickendorf": (226, 2689, 5861, 4182, 4189),
}
BERLIN_HAUS = (1321, 2533, 6307, 4366, 4336)


def baujahrsgruppe(baujahr):
    for key, von, bis, label in BAUJAHRSGRUPPEN:
        if (von is None or baujahr >= von) and (bis is None or baujahr <= bis):
            return key, label
    raise ValueError(baujahr)


def typische_spanne(typ, baujahr):
    t = HAUSTYPEN[typ]["typische"]
    if baujahr < 1949:
        return t["vor1949"], "vor 1949"
    if baujahr <= 1989:
        return t["1949-1989"], "1949 bis 1989"
    return t["ab1990"], "ab 1990"
