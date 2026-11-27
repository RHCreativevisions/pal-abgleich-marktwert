#!/usr/bin/env python3
"""Web-Fassung der Marktwert-Einschätzung (eine Datei, mobil zuerst, zum Teilen per Link).

Aufruf:  python3 scripts/webseite.py objekte/beispiel_kladow.json
Ergebnis: ausgabe/web/<name>/index.html  (alles eingebettet, eine Datei)
"""
import base64, html, json, os, sys, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bewertung as B
import marktdaten as M

E = html.escape
eur = B.eur


b64 = B.b64


def baue_web(r, pdf_name=None):
    o, seg, typ = r["o"], r["seg"], r["typ"]
    f = M.UMRECHNUNG_WF_WGF
    adresse = f"{o['strasse']}{' ' + str(o['hausnummer']) if o.get('hausnummer') else ''}"
    ort = f"{o['plz']} Berlin-{o['ortsteil']}"
    lage_txt = {"gut": "gute und sehr gute Wohnlage", "em": "einfache und mittlere Wohnlage", "ges": "alle Wohnlagen"}[r["lage_key"]]
    b26, b24 = r["brw"][2026], r["brw"].get(2024)
    trend = ""
    if b24:
        d = (b26["brw"] / b24["brw"] - 1) * 100
        trend = f"{'+' if d >= 0 else '−'}{eur(abs(d), 1)} % seit 2024"
    mk = B.marke_fuer(o)
    vorname = mk["berater"].split()[0]
    wa_text = (f"Hallo {vorname}, ich habe meine Marktwert-Einschätzung für {adresse} in {o['ortsteil']} "
               f"gesehen und hätte gern einen Termin vor Ort.")
    wa = f"https://wa.me/{mk['whatsapp']}?text=" + urllib.parse.quote(wa_text)
    tel = f"tel:{mk['telefon_e164']}"
    foto = b64(mk["berater_foto"])
    logo_hell = b64(mk["logo_hell"])
    logo_navy = b64(mk["logo_dunkel"])

    s_alle = r["seg_alle"]
    zeilen = [("Ihre Vergleichsgruppe", f"{typ['kurz']}, Bj. {r['bj_label']}, {r['lage_kurz']} · {seg[0]} Verk.",
               seg[7] / f, seg[8] / f, seg[9] / f)]
    if r["lage_key"] != "ges":
        zeilen.append(("Gleiche Bauart, alle Lagen", f"{typ['kurz']}, Bj. {r['bj_label']} · {s_alle[0]} Verk.",
                       s_alle[7] / f, s_alle[8] / f, s_alle[9] / f))
    if r["ab"]:
        a = r["ab"]
        zeilen.append((f"Alle Häuser {r['altbezirk']}", f"Ein- und Zweifamilienhäuser · {a[0]} Verk.", a[1], a[2], a[3]))
    bh = M.BERLIN_HAUS
    zeilen.append(("Alle Häuser Berlin", f"Ein- und Zweifamilienhäuser · {eur(bh[0])} Verk.", bh[1], bh[2], bh[3]))
    chart = B.spannen_svg(zeilen, (r["qm_wf"], f"Ihr Haus · {eur(r['qm_wf'])} €/m²"))

    obj = [("Objektart", typ["name"]), ("Baujahr", str(o["baujahr"])),
           ("Wohnfläche", f"{eur(o['wohnflaeche'])} m²"), ("Grundstück", f"{eur(o['grundstueck'])} m²"),
           ("Zimmer", str(o.get("zimmer", "–"))), ("Ausstattung", ", ".join(o.get("ausstattung", [])) or "–"),
           ("Modernisiert", ", ".join(o.get("modernisiert", [])) or "–"),
           ("Im Original", ", ".join(o.get("im_original", [])) or "–"), ("Energieklasse", o.get("energieklasse", "–"))]
    obj_html = "".join(f"<div class='zeile'><dt>{E(k)}</dt><dd>{E(v)}</dd></div>" for k, v in obj)

    anp = "".join(
        f"<div class='zeile'><span>{E(s['text'])}</span><b class='{'plus' if s['prozent'] > 0 else 'minus' if s['prozent'] < 0 else ''}'>"
        f"{'+' if s['prozent'] > 0 else '−' if s['prozent'] < 0 else '±'}{eur(abs(s['prozent']), 1)} %</b></div>"
        for s in r["schritte"])
    summe = sum(s["prozent"] for s in r["schritte"])
    pos_mitte = (r["mitte"] - r["unten"]) / (r["oben"] - r["unten"]) * 100
    pos_start = (r["start"] - r["unten"]) / (r["oben"] - r["unten"]) * 100
    t_boden = r["bodenwert"] / r["mitte"] * 100
    pdf_knopf = (f'<a class="knopf hell" href="{E(pdf_name)}" download>PDF herunterladen</a>' if pdf_name else "")
    beispiel = '<span class="stempel">Beispiel</span>' if o.get("beispiel") else ""

    return f'''<!doctype html>
<html lang="de"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Marktwert-Einschätzung · {E(adresse)}, {E(o["ortsteil"])} · {E(mk["name"])}</title>
<meta name="description" content="Marktwert-Spanne {eur(r['unten'])} bis {eur(r['oben'])} € nach dem {E(mk["methode"])}, auf Basis amtlicher Verkaufsdaten.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{open(os.path.join(B.HIER, "assets", "web.css")).read()}{B.farb_css()}</style>
</head>
<body>
<header class="kopf">
  <div class="innen">
    <img src="data:image/png;base64,{logo_hell}" alt="{E(mk["name"])}" class="logo">
    <a class="kopf-cta" href="{wa}">Termin anfragen</a>
  </div>
</header>

<section class="hero">
  <div class="innen">
    <div class="kicker">{E(mk["methode"])} · amtliche Vergleichsdaten {beispiel}</div>
    <h1>Was Ihr Haus in {E(o["ortsteil"])} heute wert ist</h1>
    <p class="objekt">{E(typ["name"])} · {E(adresse)}, {E(ort)}<br>Baujahr {o["baujahr"]} · {eur(o["wohnflaeche"])} m² Wohnfläche · {eur(o["grundstueck"])} m² Grundstück</p>
    <div class="wertkarte">
      <div class="label">Marktwert-Spanne</div>
      <div class="spanne"><em>{eur(r["unten"])} €</em> <span>bis</span> <em>{eur(r["oben"])} €</em></div>
      <div class="leiste"><i style="left:{pos_mitte:.1f}%"></i></div>
      <div class="drei-werte">
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
    <p class="fuer">Erstellt für {E(o["empfaenger"])} am {E(o["datum"])} von {E(mk["berater"])}</p>
  </div>
</section>

<main class="innen">
  <section class="block">
    <div class="nr">01 · Objekt und Lage</div>
    <h2>Ihr Haus und sein Boden</h2>
    <p class="lead">In Berlin steckt ein großer Teil des Hauswerts im Grundstück. Deshalb beginnt der {E(mk["methode"])} beim amtlichen Bodenrichtwert Ihrer Lage.</p>
    <div class="zwei">
      <dl class="daten">{obj_html}</dl>
      <div class="box">
        <div class="box-k">Bodenrichtwert Ihrer Zone</div>
        <div class="gross">{eur(b26["brw"])} €/m²</div>
        <div class="klein">Stichtag 01.01.2026 · GFZ {str(b26.get("gfz") or "–").replace(".", ",")}</div>
        {B.verlauf_svg(r)}
        <div class="klein">{E(trend)}. Der Gutachterausschuss leitet die Werte aus den Verkäufen des Vorjahres ab.</div>
      </div>
    </div>
    <h3>Bodenrichtwerte rund um Ihr Haus</h3>
    <div class="karte">{B.karte_svg(r)}</div>
    <div class="legende"><span><i class="dot"></i>Lage Ihres Hauses</span><span><i class="sw"></i>Wohngebiet, dunkler = höherer Wert</span><span><i class="sw schraff"></i>Wald, Wasser, Gärten</span></div>
  </section>

  <section class="block">
    <div class="nr">02 · {E(mk["methode"])}, Schritt 1</div>
    <h2>Was vergleichbare Häuser wirklich gekostet haben</h2>
    <p class="lead">Jeder notarielle Kaufvertrag in Berlin geht an den Gutachterausschuss. Wir vergleichen Ihr Haus nur mit diesen tatsächlich gezahlten Preisen, nicht mit Angebotspreisen aus Portalen.</p>
    <div class="vg">
      <div class="vg-karte haupt"><small>Ihre Vergleichsgruppe · {seg[0]} Verkäufe 2025</small><b>Ø {eur(seg[9] / f)} € je m² Wohnfläche</b>
        <span>{E(typ["titel"])}, Baujahr {E(r["bj_label"])}, {E(lage_txt)} · Spanne {eur(seg[7] / f)} bis {eur(seg[8] / f)} € · Ø Grundstück {eur(seg[3])} m²</span></div>
      <div class="vg-karte"><small>Alle Lagen · {s_alle[0]} Verkäufe</small><b>Ø {eur(s_alle[9] / f)} €/m²</b><span>gleiche Bauart und Baujahre</span></div>
      <div class="vg-karte"><small>Typischer Kaufpreis</small><b>{eur(r["typ_sp"][0])} bis {eur(r["typ_sp"][1])} €</b><span>{E(typ["kurz"])}, Baujahr {E(r["typ_bj"])}</span></div>
    </div>
    <h3>Ihr Haus im Vergleich · € je m² Wohnfläche</h3>
    <div class="chart-scroll"><div class="chart">{chart}</div></div>
    <p class="klein">Grauer Balken = Preisspanne der verkauften Häuser, Strich = Mittelwert. Der Marktbericht weist Preise je m² Geschossfläche aus, umgerechnet mit dem amtlichen Faktor 0,81 auf Wohnfläche.</p>
  </section>

  <section class="block">
    <div class="nr">03 · {E(mk["methode"])}, Schritt 2 und 3</div>
    <h2>Vom Durchschnitt zu Ihrem Haus</h2>
    <p class="lead">Ein Mittelwert ist noch kein Preis. Wir passen ihn an Grundstück, Größe und Zustand Ihres Hauses an. Jede Anpassung steht hier offen.</p>
    <div class="anp">
      <div class="zeile basis"><span>Ausgangswert der Vergleichsgruppe<small>rd. {eur(r["wgf"])} m² Geschossfläche × Ø {eur(r["basis_qm"])} €/m²</small></span><b>{eur(r["ausgang"])} €</b></div>
      {anp}
      <div class="zeile summe"><span>Anpassungen gesamt</span><b>{'+' if summe >= 0 else '−'}{eur(abs(summe), 1)} %</b></div>
      <div class="zeile ergebnis"><span>Marktwert-Mitte</span><b>{eur(r["mitte"])} €</b></div>
    </div>
    <h3>Wie sich der Wert zusammensetzt</h3>
    <div class="anteil"><div class="boden" style="width:{t_boden:.1f}%">Boden {eur(r["bodenwert"])} €</div><div class="haus">Gebäude {eur(r["mitte"] - r["bodenwert"])} €</div></div>
    <div class="start-box">
      <div>
        <div class="box-k">Schritt 3 · Startpreis</div>
        <div class="gross">{eur(r["start"])} €</div>
        <p>Wir starten im oberen Teil der Spanne, damit mehrere Käufer gleichzeitig anfragen. Ein Preis, der zu hoch startet und später sinkt, kostet am Ende meist mehr als ein klarer Start.</p>
        {f'<p class="hinweis">{E(r["start_grund"])}</p>' if r["start_grund"] else ''}
      </div>
      <div class="skala">
        <div class="band"></div>
        <div class="pkt" style="left:{pos_mitte:.1f}%"><i></i><span class="unten">Mitte<br>{eur(r["mitte"])} €</span></div>
        <div class="pkt start" style="left:{pos_start:.1f}%"><i></i><span class="oben">Start<br>{eur(r["start"])} €</span></div>
        <div class="enden"><span>{eur(r["unten"])} €</span><span>{eur(r["oben"])} €</span></div>
      </div>
    </div>
  </section>

  <section class="cta" id="kontakt">
    <img class="foto" src="data:image/jpeg;base64,{foto}" alt="{E(mk["berater"])}">
    <div class="cta-text">
      <div class="box-k gold">Ihr nächster Schritt</div>
      <h2>Machen wir aus der Spanne Ihren Preis.</h2>
      <p>Ich komme persönlich zu Ihnen nach {E(o["ortsteil"])}, schaue mir Ihr Haus an und sage Ihnen danach, was es wirklich wert ist. Unverbindlich und kostenlos.</p>
      <div class="knoepfe">
        <a class="knopf" href="{wa}">Termin per WhatsApp anfragen <span>→</span></a>
        <a class="knopf hell" href="{tel}">{E(mk["telefon_anzeige"])} anrufen</a>
        {pdf_knopf}
      </div>
      <div class="name"><b>{E(mk["berater"])}</b> · {E(mk["berater_rolle"])}</div>
    </div>
  </section>

  <section class="block quellen">
    <h3>Quellen</h3>
    <ul>
      <li>{E(M.QUELLE)}, Stand 31.07.2026, Berichtsjahr 2025, Lizenz dl-de/zero-2-0. Häuser je Altbezirk S. 50, {E(typ["titel"])} {typ["seiten"]}, Umrechnung Wohnfläche S. 49.</li>
      <li>Bodenrichtwerte zum 01.01.2024, 01.01.2025 und 01.01.2026, Gutachterausschuss für Grundstückswerte in Berlin, Geoportal Berlin, dl-de/zero-2-0.</li>
      <li>Wohnlagen nach Adressen zum Berliner Mietspiegel 2024, Geoportal Berlin. Die Mietspiegel-Wohnlage dient als Näherung für die Wohnlage im Marktbericht.</li>
    </ul>
    <h3>Wichtiger Hinweis</h3>
    <p class="klein">Diese Marktwert-Einschätzung ist kein Verkehrswertgutachten nach § 194 BauGB und ersetzt keine Bewertung durch einen Sachverständigen. Sie beruht auf amtlichen Durchschnittswerten, auf Ihren Angaben und auf den offen ausgewiesenen Anpassungen, ohne Besichtigung. {E(mk["name"])} ist ein unabhängiges Maklerunternehmen und steht in keiner Verbindung zum Gutachterausschuss.</p>
  </section>
</main>

<footer class="fuss">
  <div class="innen">
    <img src="data:image/png;base64,{logo_navy}" alt="{E(mk["name"])}">
    <div>{E(mk["firma"])} · {E(mk["adresse"])} · {E(mk["telefon_anzeige"])} · {E(mk["email"])}</div>
    <div><a href="{E(mk["impressum"])}">Impressum</a> · <a href="{E(mk["datenschutz"])}">Datenschutz</a></div>
  </div>
</footer>

<nav class="leiste-unten">
  <a class="knopf" href="{wa}">WhatsApp</a>
  <a class="knopf hell" href="{tel}">Anrufen</a>
</nav>
</body></html>'''


def main():
    pfad = sys.argv[1]
    o = json.load(open(pfad))
    r = B.bewerte(o)
    name = os.path.splitext(os.path.basename(pfad))[0]
    ziel = os.path.join(B.AUSGABE, "web", name)
    os.makedirs(ziel, exist_ok=True)
    pdf = os.path.join(B.AUSGABE, f"{B.MARKE['name']}_Marktwert_{name}.pdf")
    pdf_name = None
    if os.path.exists(pdf):
        pdf_name = os.path.basename(pdf)
        open(os.path.join(ziel, pdf_name), "wb").write(open(pdf, "rb").read())
    open(os.path.join(ziel, "index.html"), "w").write(baue_web(r, pdf_name))
    print(os.path.join(ziel, "index.html"))


if __name__ == "__main__":
    main()
