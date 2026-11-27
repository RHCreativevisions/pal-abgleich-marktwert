#!/usr/bin/env python3
"""Marktwert-Einschätzung nach dem Pal-Abgleich (Häuser in Berlin).

Aufruf:  python3 scripts/bewertung.py objekte/beispiel_kladow.json
Ergebnis: ausgabe/<name>.html und ausgabe/<name>.pdf

Live abgefragt (amtlich, kostenlos):
  - Bodenrichtwerte 01.01.2026/2025/2024, Geoportal Berlin (WFS brw2026 ...)
  - Wohnlage laut Berliner Mietspiegel 2024 (WFS wohnlagenadr2024)
  - Adresse -> Koordinate über Nominatim (OpenStreetMap), nur Straße + PLZ
Fest hinterlegt: Segmentwerte aus dem Immobilienmarktbericht 2025/26 (marktdaten.py).
"""
import json, math, os, subprocess, sys, time, urllib.parse, urllib.request, html, base64

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marktdaten as M

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Wurzel des Skills
UA = {"User-Agent": "pal-abgleich-marktwert/1.0"}
ORTSTEILE = os.path.join(HIER, "daten", "ortsteile.json")
MARKE = json.load(open(os.path.join(HIER, "marke.json")))
AUSGABE = os.environ.get("PAL_AUSGABE", os.path.join(HIER, "ausgabe"))


def b64(pfad):
    return base64.b64encode(open(os.path.join(HIER, pfad), "rb").read()).decode()


def marke_fuer(o):
    """Marke mit den Feldern, die ein Objekt überschreiben darf (berater, berater_foto, berater_rolle)."""
    m = dict(MARKE)
    for k in ("berater", "berater_foto", "berater_rolle"):
        if o.get(k):
            m[k] = o[k]
    return m


def farb_css():
    f = MARKE.get("farben", {})
    return (f":root {{ --navy:{f.get('primaer', '#222D4F')}; --creme:{f.get('hintergrund', '#F1F0E9')}; "
            f"--brass:{f.get('akzent', '#A8834A')}; --ink:{f.get('primaer', '#222D4F')}; }}")
BRW_LAYER = {2026: "brw2026:brw2026_vector", 2025: "brw2025:brw_2025_vector", 2024: "brw2024:brw_2024_vector"}


# ---------------------------------------------------------------- Helfer
def eur(x, nachkomma=0):
    s = f"{x:,.{nachkomma}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def hol_json(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def geocode(strasse, hnr, plz):
    q = f"{strasse} {hnr or ''}, {plz} Berlin".replace("  ", " ")
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1, "countrycodes": "de"})
    d = hol_json(url)
    if not d:
        raise SystemExit(f"Adresse nicht gefunden: {q}")
    return float(d[0]["lat"]), float(d[0]["lon"])


def wfs(dienst, layer, lat, lon, d, count=500):
    url = (f"https://gdi.berlin.de/services/wfs/{dienst}?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
           f"&TYPENAMES={layer}&OUTPUTFORMAT=application/json&SRSNAME=EPSG:4326&COUNT={count}"
           f"&BBOX={lat-d*0.62},{lon-d},{lat+d*0.62},{lon+d},urn:ogc:def:crs:EPSG::4326")
    return hol_json(url, timeout=90)["features"]


def ringe(geom):
    """Liefert Liste von Polygonen, jedes als Liste von Ringen [(lon,lat),...]."""
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def im_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi:
            inside = not inside
        j = i
    return inside


def enthaelt(geom, lon, lat):
    for poly in ringe(geom):
        if im_ring(lon, lat, poly[0]) and not any(im_ring(lon, lat, h) for h in poly[1:]):
            return True
    return False


def brw_am_punkt(jahr, lat, lon):
    feats = wfs(f"brw{jahr}", BRW_LAYER[jahr], lat, lon, 0.0004)
    for f in feats:
        if enthaelt(f["geometry"], lon, lat):
            return f["properties"]
    return None


def wohnlage(strasse, hnr, lat, lon):
    feats = wfs("wohnlagenadr2024", "wohnlagenadr2024:wohnlagenadr2024", lat, lon, 0.004, count=2000)
    passend = [f["properties"] for f in feats if f["properties"].get("strasse") == strasse]
    if hnr:
        exakt = [p for p in passend if p.get("hnr", "").lstrip("0") == str(hnr).lstrip("0")]
        if exakt:
            return exakt[0]["wol"], "Adresse"
    if passend:
        from collections import Counter
        wol, n = Counter(p["wol"] for p in passend).most_common(1)[0]
        return wol, f"{n} von {len(passend)} Adressen der Straße"
    return None, None


# ---------------------------------------------------------------- Bewertung
def bewerte(o):
    if o.get("lat"):
        lat, lon = o["lat"], o["lon"]
    else:
        lat, lon = geocode(o["strasse"], o.get("hausnummer"), o["plz"])
    brw = {j: brw_am_punkt(j, lat, lon) for j in (2026, 2025, 2024)}
    if not brw[2026]:
        raise SystemExit("Kein Bodenrichtwert am Punkt gefunden")
    wol, wol_basis = wohnlage(o["strasse"], o.get("hausnummer"), lat, lon)
    zonen = wfs("brw2026", BRW_LAYER[2026], lat, lon, 0.026)

    ot = json.load(open(ORTSTEILE))["ortsteile"].get(o["ortsteil"], {})
    if not ot and not o.get("altbezirk"):
        print(f"Hinweis: Ortsteil {o['ortsteil']!r} unbekannt, Bezirksvergleich entfällt. Schreibweise prüfen (daten/ortsteile.json).")
    altbezirk = ot.get("altbezirk", o.get("altbezirk"))

    bj_key, bj_label = M.baujahrsgruppe(o["baujahr"])
    typ = M.HAUSTYPEN[o["typ"]]
    lage_key = "gut" if wol in ("gut", "sehr gut") else "em"
    seg = typ["tabelle"][bj_key][lage_key]
    seg_hinweis = None
    if seg is None or seg[0] < 5:
        seg = typ["tabelle"][bj_key]["ges"]
        seg_hinweis = "Zu wenige Kauffälle in der Lageklasse, daher alle Wohnlagen der Baujahrsgruppe."
        lage_key = "ges"
    seg_alle = typ["tabelle"][bj_key]["ges"]

    wf = o["wohnflaeche"]
    wgf = wf / M.UMRECHNUNG_WF_WGF
    basis_qm = seg[9]
    ausgang = wgf * basis_qm
    brw_wert = brw[2026]["brw"]

    schritte = []
    # Grundstück gegenüber Ø der Vergleichsgruppe, bewertet mit dem Bodenrichtwert
    diff_m2 = o["grundstueck"] - seg[3]
    p_grund = max(-8.0, min(8.0, diff_m2 * brw_wert / ausgang * 100))
    schritte.append({"text": f"Grundstück {eur(o['grundstueck'])} m² statt Ø {eur(seg[3])} m² der Vergleichsgruppe"
                             f" ({'+' if diff_m2 >= 0 else '−'}{eur(abs(diff_m2))} m² × {eur(brw_wert)} €/m² Bodenrichtwert)",
                     "prozent": round(p_grund * 2) / 2})
    # Hausgröße: größere Häuser erzielen je m² etwas weniger
    rel = wgf / seg[6] - 1
    p_groesse = max(-5.0, min(5.0, -25 * rel))
    if abs(p_groesse) >= 0.5:
        schritte.append({"text": f"Hausgröße rd. {eur(wgf)} m² Geschossfläche statt Ø {eur(seg[6])} m²"
                                 f" (größere Häuser erzielen je m² etwas weniger)",
                         "prozent": round(p_groesse * 2) / 2})
    for a in o.get("anpassungen", []):
        schritte.append({"text": a["text"], "prozent": float(a["prozent"])})

    faktor = 1 + sum(s["prozent"] for s in schritte) / 100
    roh = ausgang * faktor
    mitte = round(roh / 5000) * 5000
    sp = o.get("spanne_prozent", 6.0) / 100
    unten = math.floor(mitte * (1 - sp) / 5000) * 5000
    oben = math.ceil(mitte * (1 + sp) / 5000) * 5000

    # Startpreis im oberen Teil der Spanne, aber nicht knapp über einer runden Suchgrenze
    kandidat = mitte + 0.6 * (oben - mitte)
    grenze = math.floor(kandidat / 50000) * 50000
    if 0 <= kandidat - grenze <= 0.015 * kandidat:
        start = grenze - 5000
        start_grund = (f"Knapp unter {eur(grenze)} €. Viele Käufer filtern im Portal mit runden Obergrenzen, "
                       f"ein Preis knapp darüber fällt aus genau diesen Suchen heraus.")
    else:
        start = round(kandidat / 5000) * 5000
        start_grund = None

    bodenwert = brw_wert * o["grundstueck"]
    ab = M.ALTBEZIRK_HAUS.get(altbezirk)
    typ_sp, typ_bj = M.typische_spanne(o["typ"], o["baujahr"])

    return dict(o=o, lat=lat, lon=lon, brw=brw, wol=wol, wol_basis=wol_basis, zonen=zonen,
                altbezirk=altbezirk, bj_key=bj_key, bj_label=bj_label, typ=typ, lage_key=lage_key,
                seg=seg, seg_alle=seg_alle, seg_hinweis=seg_hinweis, wgf=wgf, basis_qm=basis_qm,
                ausgang=ausgang, schritte=schritte, roh=roh, mitte=mitte, unten=unten, oben=oben,
                start=start, start_grund=start_grund, bodenwert=bodenwert, ab=ab,
                typ_sp=typ_sp, typ_bj=typ_bj, qm_wf=mitte / wf,
                lage_kurz={"gut": "gute Lage", "em": "einf./mittl. Lage", "ges": "alle Lagen"}[lage_key])


# ---------------------------------------------------------------- Grafiken (Inline-SVG)
_F = MARKE.get("farben", {})
NAVY, CREME, BRASS, INK2, LINE = (_F.get("primaer", "#222D4F"), _F.get("hintergrund", "#F1F0E9"),
                                  _F.get("akzent", "#A8834A"), "#5B6275", "#D9D6CB")


def karte_svg(r, w=560, h=215):
    lat0, lon0 = r["lat"], r["lon"]
    kx = math.cos(math.radians(lat0)) * 111320
    ky = 110540
    halb_b = 1500  # Meter links/rechts
    s = w / (2 * halb_b)

    def p(lon, lat):
        return (w / 2 + (lon - lon0) * kx * s, h / 2 - (lat - lat0) * ky * s)

    w_werte = sorted({f["properties"]["brw"] for f in r["zonen"] if f["properties"]["nutzung"].startswith("W")})
    lo, hi = (min(w_werte), max(w_werte)) if w_werte else (0, 1)

    def farbe(v):  # eine Farbe, hell -> dunkel
        t = 0.0 if hi == lo else (v - lo) / (hi - lo)
        a = (224, 221, 208); b = (64, 80, 128)
        return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * (0.25 + 0.75 * t)) for i in range(3))

    teile, labels = [], []
    for f in r["zonen"]:
        pr = f["properties"]
        istw = pr["nutzung"].startswith("W")
        for poly in ringe(f["geometry"]):
            d = ""
            for ring in poly:
                pts = [p(x, y) for x, y in ring]
                d += "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z "
            eigene = enthaelt(f["geometry"], lon0, lat0)
            fill = farbe(pr["brw"]) if istw else "url(#schraffur)"
            teile.append(f'<path d="{d}" fill="{fill}" fill-rule="evenodd" stroke="#fff" stroke-width="{2.2 if eigene else 1.2}"/>')
            if istw:
                innen = [p(x, y) for x, y in poly[0]]
                innen = [(x, y) for x, y in innen if 30 < x < w - 30 and 18 < y < h - 18]
                if len(innen) >= 3:
                    cx = sum(x for x, _ in innen) / len(innen)
                    cy = sum(y for _, y in innen) / len(innen)
                    if eigene:
                        cx, cy = w / 2, h / 2 - 34
                    labels.append((cx, cy, pr["brw"], pr.get("gfz"), eigene))
    lab_svg = ""
    for cx, cy, v, gfz, eigene in labels:
        bg = NAVY if eigene else "#ffffff"
        fg = "#ffffff" if eigene else NAVY
        txt = f"{eur(v)} €/m²"
        bw = 74 if eigene else 66
        lab_svg += (f'<g transform="translate({cx:.0f},{cy:.0f})"><rect x="{-bw/2}" y="-11" width="{bw}" height="22" rx="11" fill="{bg}" '
                    f'stroke="{NAVY}" stroke-width="{0 if eigene else 0.8}"/><text y="4.2" text-anchor="middle" font-size="11" '
                    f'font-weight="{700 if eigene else 600}" fill="{fg}">{txt}</text></g>')
    marker = (f'<g transform="translate({w/2},{h/2})"><circle r="14" fill="{BRASS}" opacity=".22"/>'
              f'<circle r="6.5" fill="{BRASS}" stroke="#fff" stroke-width="2.5"/></g>')
    massstab = (f'<g transform="translate({w-118},{h-16})"><rect x="-6" y="-14" width="112" height="22" rx="4" fill="#ffffffcc"/>'
                f'<line x1="0" y1="0" x2="{500*s:.1f}" y2="0" stroke="{NAVY}" stroke-width="2"/>'
                f'<text x="{500*s/2:.1f}" y="-4" text-anchor="middle" font-size="9" fill="{NAVY}">500 m</text></g>')
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">'
            f'<defs><clipPath id="k"><rect width="{w}" height="{h}" rx="10"/></clipPath>'
            f'<pattern id="schraffur" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="7" height="7" fill="#EEECE4"/><line x1="0" y1="0" x2="0" y2="7" stroke="#D8D4C6" stroke-width="2"/></pattern></defs>'
            f'<g clip-path="url(#k)"><rect width="{w}" height="{h}" fill="#EEECE4"/>{"".join(teile)}{marker}{lab_svg}{massstab}</g>'
            f'<rect width="{w}" height="{h}" rx="10" fill="none" stroke="{LINE}"/></svg>')


def verlauf_svg(r, w=250, h=150):
    werte = [(j, r["brw"][j]["brw"]) for j in (2024, 2025, 2026) if r["brw"].get(j)]
    top = max(v for _, v in werte) * 1.18
    bw, gap, x0, base = 46, 30, 22, h - 26
    out = []
    for i, (j, v) in enumerate(werte):
        x = x0 + i * (bw + gap)
        bh = (v / top) * (base - 14)
        fill = NAVY if j == 2026 else "#AEB3C2"
        out.append(f'<path d="M{x},{base} V{base-bh+4} Q{x},{base-bh} {x+4},{base-bh} H{x+bw-4} Q{x+bw},{base-bh} {x+bw},{base-bh+4} V{base} Z" fill="{fill}"/>')
        out.append(f'<text x="{x+bw/2}" y="{base-bh-6}" text-anchor="middle" font-size="11.5" font-weight="700" fill="{NAVY}">{eur(v)} €</text>')
        out.append(f'<text x="{x+bw/2}" y="{base+15}" text-anchor="middle" font-size="10" fill="{INK2}">01.01.{j}</text>')
    out.append(f'<line x1="10" y1="{base}" x2="{w-10}" y2="{base}" stroke="{LINE}"/>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">{"".join(out)}</svg>'


def spannen_svg(zeilen, marker, w=640):
    """zeilen: (titel, untertitel, von, bis, mittel); marker: (wert, label). Alles €/m² Wohnfläche."""
    rh, top, links, rechts = 46, 30, 215, 24
    h = top + rh * len(zeilen) + 20
    lo = min(z[2] for z in zeilen + [("", "", marker[0], 0, 0)])
    hi = max(z[3] for z in zeilen)
    lo = math.floor(lo * 0.92 / 500) * 500
    hi = math.ceil(hi * 1.03 / 500) * 500
    sx = lambda v: links + (v - lo) / (hi - lo) * (w - links - rechts)
    out = []
    for t in range(int(lo), int(hi) + 1, 1000 if hi - lo > 6000 else 500):
        x = sx(t)
        out.append(f'<line x1="{x:.1f}" y1="{top-6}" x2="{x:.1f}" y2="{h-16}" stroke="#E6E3D9"/>')
        out.append(f'<text x="{x:.1f}" y="{h-3}" text-anchor="middle" font-size="9" fill="{INK2}">{eur(t)}</text>')
    for i, (titel, unter, von, bis, mittel) in enumerate(zeilen):
        y = top + i * rh + 14
        out.append(f'<text x="0" y="{y-1}" font-size="11.5" font-weight="600" fill="{NAVY}">{html.escape(titel)}</text>')
        out.append(f'<text x="0" y="{y+13}" font-size="9.5" fill="{INK2}">{html.escape(unter)}</text>')
        x1, x2 = sx(von), sx(bis)
        out.append(f'<rect x="{x1:.1f}" y="{y-5}" width="{x2-x1:.1f}" height="12" rx="6" fill="#C9CDD8"/>')
        xm = sx(mittel)
        out.append(f'<rect x="{xm-1.5:.1f}" y="{y-9}" width="3" height="20" rx="1.5" fill="{NAVY}"/>')
        out.append(f'<text x="{xm:.1f}" y="{y+24}" text-anchor="middle" font-size="9.5" font-weight="600" fill="{NAVY}">Ø {eur(mittel)}</text>')
    xm = sx(marker[0])
    out.append(f'<line x1="{xm:.1f}" y1="{top-14}" x2="{xm:.1f}" y2="{h-16}" stroke="{BRASS}" stroke-width="2" stroke-dasharray="4 3"/>')
    out.append(f'<rect x="{xm-62:.1f}" y="{top-30}" width="124" height="19" rx="9.5" fill="{BRASS}"/>')
    out.append(f'<text x="{xm:.1f}" y="{top-17}" text-anchor="middle" font-size="10" font-weight="700" fill="#fff">{html.escape(marker[1])}</text>')
    return (f'<svg viewBox="0 -2 {w} {h+4}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">'
            f'{"".join(out)}</svg>')


def anteil_svg(boden, gesamt, w=640, h=64):
    t = boden / gesamt
    xb = w * t
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">'
            f'<rect x="0" y="6" width="{xb-1:.1f}" height="26" rx="5" fill="{NAVY}"/>'
            f'<rect x="{xb+1:.1f}" y="6" width="{w-xb-1:.1f}" height="26" rx="5" fill="#C9CDD8"/>'
            f'<text x="10" y="23.5" font-size="11" font-weight="700" fill="#fff">Boden {eur(boden)} € · {round(t*100)} %</text>'
            f'<text x="{w-10}" y="23.5" text-anchor="end" font-size="11" font-weight="700" fill="{NAVY}">Gebäude {eur(gesamt-boden)} € · {round((1-t)*100)} %</text>'
            f'<text x="0" y="52" font-size="9.5" fill="{INK2}">Bodenrichtwert × Grundstücksfläche</text>'
            f'<text x="{w}" y="52" text-anchor="end" font-size="9.5" fill="{INK2}">Marktwert-Mitte abzüglich Bodenwert</text></svg>')


# ---------------------------------------------------------------- HTML
def baue_html(r):
    o, seg, typ = r["o"], r["seg"], r["typ"]
    E = html.escape
    mk = marke_fuer(o)
    logo_hell = b64(mk["logo_hell"])
    logo_navy = b64(mk["logo_dunkel"])
    adresse = f"{o['strasse']}{' ' + str(o['hausnummer']) if o.get('hausnummer') else ''}"
    ort = f"{o['plz']} Berlin-{o['ortsteil']}"
    lage_txt = {"gut": "gute und sehr gute Wohnlage", "em": "einfache und mittlere Wohnlage", "ges": "alle Wohnlagen"}[r["lage_key"]]
    f = M.UMRECHNUNG_WF_WGF
    b26, b25, b24 = r["brw"][2026], r["brw"].get(2025), r["brw"].get(2024)
    brw_trend = ""
    if b24:
        d = (b26["brw"] / b24["brw"] - 1) * 100
        brw_trend = f"{'+' if d >= 0 else '−'}{eur(abs(d), 1)} % seit 2024"
    beispiel = '<div class="stempel">Beispiel</div>' if o.get("beispiel") else ""

    def fuss(n):
        return (f'<div class="fuss"><span>{E(mk["name"])} · Marktwert-Einschätzung · {E(adresse)}, {E(ort)}</span>'
                f'<span>Seite {n} von 5</span></div>')

    # ---- Seite 1
    s1 = f'''
<section class="seite titel">
  <div class="kopfband">
    <img class="logo" src="data:image/png;base64,{logo_hell}" alt="{E(mk["name"])}">
    <div class="kopf-r">Marktwert-Einschätzung<br>Stand {E(o["datum"])}</div>
  </div>
  {beispiel}
  <div class="titel-inhalt">
    <div class="kicker">{E(mk["methode"])} · amtliche Vergleichsdaten</div>
    <h1>Was Ihr Haus in {E(o["ortsteil"])} heute wert ist</h1>
    <p class="objektzeile">{E(typ["name"])} · {E(adresse)} · {E(ort)}<br>
       Baujahr {o["baujahr"]} · {eur(o["wohnflaeche"])} m² Wohnfläche · {eur(o["grundstueck"])} m² Grundstück</p>

    <div class="wertkarte">
      <div class="wk-label">Marktwert-Spanne</div>
      <div class="wk-spanne">{eur(r["unten"])} € <span>bis</span> {eur(r["oben"])} €</div>
      <div class="wk-leiste">
        <div class="wk-band"></div>
        <div class="wk-mitte"></div>
      </div>
      <div class="wk-unten">
        <div><small>Mittelwert</small><b>{eur(r["mitte"])} €</b></div>
        <div><small>je m² Wohnfläche</small><b>{eur(r["qm_wf"])} €</b></div>
        <div class="start"><small>Empfohlener Startpreis</small><b>{eur(r["start"])} €</b></div>
      </div>
    </div>

    <div class="fakten">
      <div><b>{eur(b26["brw"])} €/m²</b><span>Bodenrichtwert 01.01.2026</span></div>
      <div><b>{seg[0]} Verkäufe</b><span>amtliche Vergleichsgruppe 2025</span></div>
      <div><b>Wohnlage {E(r["wol"] or "–")}</b><span>Berliner Mietspiegel 2024</span></div>
    </div>
  </div>
    <div class="weg">
      <div class="weg-k">So ist dieser Wert entstanden</div>
      <div class="weg-reihe">
        <div><b>1</b><h4>Amtliche Verkaufspreise</h4><p>{seg[0]} notariell verkaufte Häuser gleicher Bauart, gleichen Alters und gleicher Lagequalität.</p></div>
        <div><b>2</b><h4>Anpassung an Ihr Haus</h4><p>Grundstück, Größe und Zustand, jede Anpassung offen ausgewiesen.</p></div>
        <div><b>3</b><h4>Startpreis</h4><p>Ein Preis, zu dem mehrere Käufer gleichzeitig anfragen.</p></div>
      </div>
    </div>
  <div class="titel-fuss">
    <div>Erstellt für <b>{E(o["empfaenger"])}</b><br>von {E(mk["berater"])}, {E(mk["name"])}</div>
    <div class="tf-r">Jede Zahl mit amtlicher Quelle.<br>Grundlage sind notarielle Kaufpreise, keine Angebotspreise.</div>
  </div>
</section>'''

    # ---- Seite 2
    zeilen_obj = [
        ("Objektart", typ["name"]), ("Adresse", f"{adresse}, {ort}"), ("Baujahr", str(o["baujahr"])),
        ("Wohnfläche", f"{eur(o['wohnflaeche'])} m² (rd. {eur(r['wgf'])} m² Geschossfläche)"),
        ("Grundstück", f"{eur(o['grundstueck'])} m²"), ("Zimmer", str(o.get("zimmer", "–"))),
        ("Ausstattung", ", ".join(o.get("ausstattung", [])) or "–"),
        ("Modernisiert", ", ".join(o.get("modernisiert", [])) or "–"),
        ("Im Original", ", ".join(o.get("im_original", [])) or "–"),
        ("Energieklasse", o.get("energieklasse", "–")),
    ]
    tab_obj = "".join(f"<tr><th>{E(k)}</th><td>{E(v)}</td></tr>" for k, v in zeilen_obj)
    s2 = f'''
<section class="seite">
  <div class="sk"><img src="data:image/png;base64,{logo_navy}" alt=""><span>01 · Objekt und Lage</span></div>
  <h2>Ihr Haus und sein Boden</h2>
  <p class="lead">In Berlin steckt ein großer Teil des Hauswerts im Grundstück. Deshalb beginnt der {E(mk["methode"])} beim amtlichen Bodenrichtwert Ihrer Lage.</p>
  <div class="zwei">
    <table class="daten">{tab_obj}</table>
    <div class="box">
      <div class="box-k">Bodenrichtwert Ihrer Zone</div>
      <div class="gross">{eur(b26["brw"])} €/m²</div>
      <div class="klein">Stichtag 01.01.2026 · {E(b26["nutzung"])} · GFZ {str(b26.get("gfz") or "–").replace(".", ",")} · {E(b26["beitragszustand"])}</div>
      {verlauf_svg(r)}
      <div class="klein">{E(brw_trend)}. Der Gutachterausschuss leitet die Werte aus den Verkäufen des Vorjahres ab.</div>
    </div>
  </div>
  <h3>Bodenrichtwerte rund um Ihr Haus</h3>
  <div class="karte">{karte_svg(r)}</div>
  <div class="legende"><span><i class="dot" style="background:{BRASS}"></i>Lage Ihres Hauses</span>
    <span><i class="sw" style="background:#404F80"></i>Wohngebiet, dunkler = höherer Bodenrichtwert</span>
    <span><i class="sw schraff"></i>Wald, Wasser, Gärten, Sonderflächen</span></div>
  <p class="quelle">Quelle Bodenrichtwerte 01.01.2024 bis 01.01.2026, Gutachterausschuss für Grundstückswerte in Berlin, Geoportal Berlin (WFS), dl-de/zero-2-0.
   Wohnlage laut Straßenverzeichnis zum Berliner Mietspiegel 2024 ({E(r["wol_basis"] or "")}).</p>
  {fuss(2)}
</section>'''

    # ---- Seite 3
    s_alle = r["seg_alle"]
    zeilen = [
        ("Ihre Vergleichsgruppe", f"{typ['kurz']}, Bj. {r['bj_label']}, {r['lage_kurz']} · {seg[0]} Verk.",
         seg[7] / f, seg[8] / f, seg[9] / f),
    ]
    if r["lage_key"] != "ges":
        zeilen.append(("Gleiche Bauart, alle Lagen", f"{typ['kurz']}, Bj. {r['bj_label']} · {s_alle[0]} Verk.",
                       s_alle[7] / f, s_alle[8] / f, s_alle[9] / f))
    if r["ab"]:
        a = r["ab"]
        zeilen.append((f"Alle Häuser {r['altbezirk']}", f"Ein- und Zweifamilienhäuser · {a[0]} Verk.", a[1], a[2], a[3]))
    bh = M.BERLIN_HAUS
    zeilen.append(("Alle Häuser Berlin", f"Ein- und Zweifamilienhäuser · {eur(bh[0])} Verk.", bh[1], bh[2], bh[3]))
    chart = spannen_svg(zeilen, (r["qm_wf"], f"Ihr Haus · {eur(r['qm_wf'])} €/m²"))

    vg = [
        (f"{typ['titel']}, Baujahr {r['bj_label']}, {lage_txt}", seg[0],
         f"{eur(seg[1])}–{eur(seg[2])} m² · Ø {eur(seg[3])}", f"{eur(seg[4])}–{eur(seg[5])} m² · Ø {eur(seg[6])}",
         f"{eur(seg[7])}–{eur(seg[8])} · <b>Ø {eur(seg[9])}</b>", typ["seiten"]),
        (f"{typ['titel']}, Baujahr {r['bj_label']}, alle Lagen", s_alle[0],
         f"{eur(s_alle[1])}–{eur(s_alle[2])} m² · Ø {eur(s_alle[3])}", f"{eur(s_alle[4])}–{eur(s_alle[5])} m² · Ø {eur(s_alle[6])}",
         f"{eur(s_alle[7])}–{eur(s_alle[8])} · Ø {eur(s_alle[9])}", typ["seiten"]),
    ]
    vg_html = "".join(f"<tr><td>{E(a)}</td><td class='z'>{b}</td><td>{c}</td><td>{d}</td><td>{e}</td><td class='q'>{g}</td></tr>"
                      for a, b, c, d, e, g in vg)
    s3 = f'''
<section class="seite">
  <div class="sk"><img src="data:image/png;base64,{logo_navy}" alt=""><span>02 · {E(mk["methode"])}, Schritt 1</span></div>
  <h2>Was vergleichbare Häuser wirklich gekostet haben</h2>
  <p class="lead">Jeder notarielle Kaufvertrag in Berlin geht an den Gutachterausschuss. Wir vergleichen Ihr Haus nur mit diesen tatsächlich gezahlten Preisen, nicht mit Angebotspreisen aus Portalen.</p>
  <h3>Amtliche Vergleichsgruppen 2025</h3>
  <table class="vg">
    <thead><tr><th>Vergleichsgruppe</th><th class='z'>Verkäufe</th><th>Grundstück</th><th>Geschossfläche</th><th>Kaufpreis €/m² Geschossfl.</th><th>Quelle</th></tr></thead>
    <tbody>{vg_html}</tbody>
  </table>
  <p class="klein">Spanne und Mittel nach Ausreißerbereinigung (10 %). Der Bericht weist Preise je m² wertrelevanter Geschossfläche aus, im Mittel entsprechen 100 m² Geschossfläche rd. 81 m² Wohnfläche (S. 49).{(' ' + E(r['seg_hinweis'])) if r['seg_hinweis'] else ''}</p>

  <h3>Ihr Haus im Vergleich · € je m² Wohnfläche</h3>
  <div class="chart">{chart}</div>
  <p class="klein">Grauer Balken = Preisspanne der verkauften Häuser, Strich = Mittelwert. Vergleichsgruppen in €/m² Geschossfläche über den Faktor 0,81 auf Wohnfläche umgerechnet, Bezirks- und Berlinwerte sind amtlich je m² Wohnfläche (S. 50).</p>

  <div class="drei">
    <div class="mini"><small>Typischer Kaufpreis, {E(typ["kurz"])} Baujahr {E(r["typ_bj"])}</small><b>{eur(r["typ_sp"][0])} bis {eur(r["typ_sp"][1])} €</b><span>deckt zwei Drittel der Verkäufe ab · {typ["typ_seite"]}</span></div>
    <div class="mini"><small>Durchschnitt aller {E(typ["dativ"])} in Berlin</small><b>{eur(typ["mittel_kaufpreis"])} €</b><span>Verkäufe 2025 · {typ["typ_seite"]}</span></div>
    <div class="mini dunkel"><small>Ihr Haus, Mittelwert</small><b>{eur(r["mitte"])} €</b><span>{eur(r["qm_wf"])} € je m² Wohnfläche</span></div>
  </div>
  {fuss(3)}
</section>'''

    # ---- Seite 4
    zeilen_anp = "".join(
        f"<tr><td>{E(s['text'])}</td><td class='p {'plus' if s['prozent'] > 0 else 'minus' if s['prozent'] < 0 else ''}'>"
        f"{'+' if s['prozent'] > 0 else '−' if s['prozent'] < 0 else '±'}{eur(abs(s['prozent']), 1)} %</td></tr>"
        for s in r["schritte"])
    summe = sum(s["prozent"] for s in r["schritte"])
    s4 = f'''
<section class="seite">
  <div class="sk"><img src="data:image/png;base64,{logo_navy}" alt=""><span>03 · {E(mk["methode"])}, Schritt 2 und 3</span></div>
  <h2>Vom Durchschnitt zu Ihrem Haus</h2>
  <p class="lead">Ein Mittelwert ist noch kein Preis. Im zweiten Schritt passen wir ihn an Grundstück, Größe und Zustand Ihres Hauses an. Jede Anpassung steht hier offen.</p>
  <table class="anp">
    <tr class="basis"><td>Ausgangswert der Vergleichsgruppe<br><small>rd. {eur(r["wgf"])} m² Geschossfläche × Ø {eur(r["basis_qm"])} €/m²</small></td><td class="p">{eur(r["ausgang"])} €</td></tr>
    {zeilen_anp}
    <tr class="summe"><td>Anpassungen gesamt</td><td class="p">{'+' if summe >= 0 else '−'}{eur(abs(summe), 1)} %</td></tr>
    <tr class="ergebnis"><td>Marktwert-Mitte (gerundet)</td><td class="p">{eur(r["mitte"])} €</td></tr>
  </table>

  <h3>Wie sich der Wert zusammensetzt</h3>
  <div class="chart">{anteil_svg(r["bodenwert"], r["mitte"])}</div>
  <p class="klein">Bodenwert {eur(o["grundstueck"])} m² × {eur(b26["brw"])} €/m². Der Gebäudeanteil entspricht rd. {eur((r["mitte"]-r["bodenwert"])/r["wgf"])} € je m² Geschossfläche, für ein Haus von {o["baujahr"]} ein plausibler Wert.</p>

  <div class="schritt3">
    <div class="s3-l">
      <div class="box-k">Schritt 3 · Startpreis</div>
      <div class="gross hell">{eur(r["start"])} €</div>
      <p>Wir starten im oberen Teil der Spanne, damit mehrere Käufer gleichzeitig anfragen. Ein Preis, der zu hoch startet und später sinkt, kostet am Ende meist mehr als ein klarer Start.</p>
      {f'<p class="hinweis">{E(r["start_grund"])}</p>' if r["start_grund"] else ''}
    </div>
    <div class="s3-r">
      <div class="skala">
        <div class="sk-band"></div>
        <div class="sk-pkt" style="left:{(r['mitte']-r['unten'])/(r['oben']-r['unten'])*100:.1f}%"><i></i><span>Mitte<br>{eur(r["mitte"])} €</span></div>
        <div class="sk-pkt start" style="left:{(r['start']-r['unten'])/(r['oben']-r['unten'])*100:.1f}%"><i></i><span>Start<br>{eur(r["start"])} €</span></div>
      </div>
      <div class="sk-enden"><span>{eur(r["unten"])} €</span><span>{eur(r["oben"])} €</span></div>
    </div>
  </div>
  {fuss(4)}
</section>'''

    # ---- Seite 5
    foto = b64(mk["berater_foto"])
    vorname = mk["berater"].split()[0]
    wa_text = (f"Hallo {vorname}, ich habe meine Marktwert-Einschätzung für {adresse} in {o['ortsteil']} "
               f"bekommen und hätte gern einen Termin vor Ort.")
    wa_link = f"https://wa.me/{mk['whatsapp']}?text=" + urllib.parse.quote(wa_text)
    s5 = f'''
<section class="seite">
  <div class="sk"><img src="data:image/png;base64,{logo_navy}" alt=""><span>04 · Nächster Schritt</span></div>
  <h2>Aus der Spanne wird ein Preis</h2>
  <p class="lead">Diese Einschätzung beruht auf amtlichen Daten und Ihren Angaben. Was sie nicht sieht, sind Dinge wie Grundriss, Licht, Nachbarschaft und der Zustand im Detail. Das klären wir bei einem Termin vor Ort.</p>
  <div class="naechste">
    <div><b>1</b><h4>Besichtigung</h4><p>Wir schauen uns Ihr Haus an und machen aus der Spanne einen konkreten Wert.</p></div>
    <div><b>2</b><h4>Unterlagen</h4><p>Grundbuch, Flurkarte, Energieausweis und Baupläne prüfen wir für Sie vorab.</p></div>
    <div><b>3</b><h4>Startpreis festlegen</h4><p>Erst wenn der Wert sitzt, legen wir gemeinsam den Startpreis fest.</p></div>
  </div>
  <div class="cta">
    <img class="cta-foto" src="data:image/jpeg;base64,{foto}" alt="{E(mk["berater"])}">
    <div class="cta-text">
      <div class="cta-k">Ihr nächster Schritt</div>
      <div class="cta-h">Machen wir aus der Spanne Ihren Preis.</div>
      <p>Ich komme persönlich zu Ihnen nach {E(o["ortsteil"])}, schaue mir Ihr Haus an und sage Ihnen danach, was es wirklich wert ist. Unverbindlich und kostenlos.</p>
      <a class="cta-btn" href="{wa_link}">Termin per WhatsApp anfragen <span>→</span></a>
      <div class="cta-neben">oder direkt anrufen <a href="tel:{mk['telefon_e164']}">{E(mk["telefon_anzeige"])}</a></div>
    </div>
    <div class="cta-name"><b>{E(mk["berater"])}</b><span>{E(mk["berater_rolle"])}</span></div>
  </div>

  <h3>Quellen</h3>
  <ul class="quellen">
    <li>{E(M.QUELLE)}, Stand 31.07.2026, Berichtsjahr 2025, Lizenz dl-de/zero-2-0. Häuser je Altbezirk S. 50, {E(typ["titel"])} {typ["seiten"]}, Umrechnung Wohnfläche S. 49.</li>
    <li>Bodenrichtwerte zum 01.01.2024, 01.01.2025 und 01.01.2026, Gutachterausschuss für Grundstückswerte in Berlin, abgerufen über das Geoportal Berlin am {E(o["datum"])}.</li>
    <li>Wohnlagen nach Adressen zum Berliner Mietspiegel 2024, Geoportal Berlin. Der Marktbericht ordnet Verkäufe nach den Wohnlagen der Kaufpreissammlung, die Mietspiegel-Wohnlage dient hier als Näherung.</li>
  </ul>
  <h3>Wichtiger Hinweis</h3>
  <p class="klein">Diese Marktwert-Einschätzung ist kein Verkehrswertgutachten nach § 194 BauGB und ersetzt keine Bewertung durch einen Sachverständigen. Sie beruht auf amtlichen Durchschnittswerten, auf Ihren Angaben und auf den offen ausgewiesenen Anpassungen, ohne Besichtigung. Die amtlichen Daten bilden Verkäufe des Jahres 2025 ab. Die Spanne von ±{eur(o.get("spanne_prozent", 6), 0)} % um den Mittelwert berücksichtigt diese Unsicherheit. {E(mk["name"])} ist ein unabhängiges Maklerunternehmen und steht in keiner Verbindung zum Gutachterausschuss.</p>
  {fuss(5)}
</section>'''

    css = open(os.path.join(HIER, "assets", "stil.css")).read() + farb_css()
    return f'''<!doctype html><html lang="de"><head><meta charset="utf-8">
<title>Marktwert-Einschätzung {E(adresse)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{css}</style></head><body>{s1}{s2}{s3}{s4}{s5}</body></html>'''


# ---------------------------------------------------------------- PDF
def finde_chrome():
    import shutil
    kandidaten = [os.environ.get("CHROME_PATH", ""),
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
    kandidaten += [shutil.which(n) or "" for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge")]
    for k in kandidaten:
        if k and os.path.exists(k):
            return k
    raise SystemExit("Kein Chrome/Chromium/Edge gefunden. Pfad per Umgebungsvariable CHROME_PATH setzen.")


def drucke_pdf(html_pfad, pdf_pfad):
    chrome = finde_chrome()
    profil = os.path.join(os.environ.get("TMPDIR", "/tmp"), "pal_abgleich_pdf_profil")
    if os.path.exists(pdf_pfad):
        os.remove(pdf_pfad)
    p = subprocess.Popen([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--use-mock-keychain",
                          f"--user-data-dir={profil}", "--virtual-time-budget=15000",
                          f"--print-to-pdf={pdf_pfad}", "file://" + urllib.request.pathname2url(html_pfad) if os.name == "nt" else "file://" + html_pfad],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0, last = time.time(), -1
    while time.time() - t0 < 90:
        time.sleep(1)
        if os.path.exists(pdf_pfad):
            size = os.path.getsize(pdf_pfad)
            if size == last and size > 0 and open(pdf_pfad, "rb").read()[-1024:].rstrip().endswith(b"%%EOF"):
                break
            last = size
    p.terminate()
    if os.name != "nt":
        subprocess.run(["pkill", "-f", profil])


def main():
    pfad = sys.argv[1]
    o = json.load(open(pfad))
    r = bewerte(o)
    name = os.path.splitext(os.path.basename(pfad))[0]
    os.makedirs(AUSGABE, exist_ok=True)
    hp = os.path.join(AUSGABE, f"{name}.html")
    pp = os.path.join(AUSGABE, f"{MARKE['name']}_Marktwert_{name}.pdf")
    open(hp, "w").write(baue_html(r))
    json.dump({k: v for k, v in r.items() if k not in ("zonen", "typ", "o")}, open(os.path.join(AUSGABE, f"{name}_rechnung.json"), "w"),
              ensure_ascii=False, indent=1, default=str)
    print(f"Bodenrichtwert {r['brw'][2026]['brw']} | Wohnlage {r['wol']} | Segment {r['bj_key']}/{r['lage_key']} n={r['seg'][0]}")
    print(f"Ausgang {r['ausgang']:.0f} | Anpassungen {[s['prozent'] for s in r['schritte']]} | Mitte {r['mitte']} | Spanne {r['unten']}-{r['oben']} | Start {r['start']}")
    if "--kein-pdf" not in sys.argv:
        drucke_pdf(hp, pp)
        print(pp)


if __name__ == "__main__":
    main()
