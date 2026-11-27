---
name: pal-abgleich-marktwert
description: Erstellt eine Marktwert-Einschätzung für ein Haus in Berlin nach dem Pal-Abgleich, als 5-seitiges PDF und als teilbare Webseite mit Kontakt-Button. Rechnet mit amtlichen Daten des Gutachterausschusses Berlin (Bodenrichtwert live vom Geoportal, Kaufpreise je Bauart, Baujahr und Wohnlage aus dem Immobilienmarktbericht 2025/26), passt sie offen an Grundstück, Größe und Zustand an und schlägt eine Spanne und einen Startpreis vor. Immer verwenden, wenn jemand eine Immobilienbewertung, Marktwert-Einschätzung, Wertermittlung, Ersteinschätzung, Preiseinschätzung oder einen Pal-Abgleich für einen Lead oder Eigentümer in Berlin machen will, auch wenn nur „bewerte das Haus in Kladow“, „was ist das Haus wert“ oder „mach die Bewertung für den neuen Lead“ fällt.
---

# Pal-Abgleich · Marktwert-Einschätzung für Häuser in Berlin

Der Pal-Abgleich hat drei Schritte.
1. **Amtliche Verkaufspreise** statt Angebotspreise. Ausgangswert ist der Mittelwert der passenden Vergleichsgruppe des Gutachterausschusses (Bauart × Baujahr × Wohnlage).
2. **Anpassung an das Haus.** Grundstück (über den Bodenrichtwert), Hausgröße, Zustand und Ausstattung, jede Anpassung offen ausgewiesen.
3. **Startpreis.** Im oberen Teil der Spanne, knapp unter runden Suchgrenzen der Portale.

Ergebnis sind ein PDF (5 Seiten) und eine Webseite (eine HTML-Datei) im Design aus `marke.json`.

## Voraussetzungen

- Python 3.9 oder neuer, nur Standardbibliothek
- Google Chrome, Chromium oder Edge für das PDF (sonst Pfad in `CHROME_PATH`)
- Internet für das Geoportal Berlin (Bodenrichtwert, Wohnlage) und Nominatim (Adresse → Koordinate)

## Ablauf

### 1. Angaben einsammeln

Pflicht sind Straße, PLZ, Ortsteil, Haustyp, Baujahr, Wohnfläche und Grundstücksfläche. Hausnummer macht Bodenrichtwert und Wohnlage genauer. Fehlt etwas, frag nach statt zu raten.

| Feld | Werte |
|---|---|
| `typ` | `freistehend`, `doppelhaus` oder `reihenhaus` |
| `ortsteil` | amtlicher Name wie in `daten/ortsteile.json` (z. B. `Kladow`, `Lichterfelde`). Bei Unklarheit über `plz` in derselben Datei nachschlagen |
| `empfaenger`, `datum` | z. B. „Familie Muster“, „27.11.2026“ |
| `ausstattung`, `modernisiert`, `im_original` | kurze Listen, erscheinen so im Dokument |
| `anpassungen` | Zu- und Abschläge in Prozent, siehe Schritt 2 |
| `spanne_prozent` | Standard 6. Bei vielen Unbekannten 8, nach Besichtigung 4 |
| `beispiel` | `true` setzt den Stempel „Beispiel“, für echte Leads `false` |

Vorlage ist `objekte/beispiel_kladow.json`. Für jeden Lead eine eigene Datei `objekte/<kurzname>.json` anlegen. Lead-Dateien sind per `.gitignore` vom Repo ausgeschlossen und dürfen nie committet werden.

### 2. Anpassungen festlegen

Grundstück und Hausgröße rechnet das Skript selbst, nicht doppelt eintragen. Für Zustand, Ausstattung und Mikrolage gelten diese Erfahrungswerte (keine amtlichen Werte, im Zweifel den Berater fragen).

| Merkmal | Anpassung |
|---|---|
| Dach, Fassade, Fenster im Original, Energieklasse E bis H | −4 bis −10 % |
| Sichtbarer Sanierungsstau (Feuchte, alte Elektrik, Asbest) | −5 bis −15 % |
| Heizung, Bad oder Fenster in den letzten 15 Jahren erneuert | +2 bis +5 % |
| Kernsaniert oder Energieklasse A/B | +8 bis +15 % |
| Vollkeller, Garage, Kamin, Wintergarten | je +0,5 bis +1 %, zusammen höchstens +3 % |
| Hauptstraße, Bahn, Fluglärm | −3 bis −8 % |
| Wasser- oder Waldrandlage, ruhige Sackgasse | +3 bis +10 % |

Zusammen liegen die Anpassungen meist zwischen −15 und +15 %. Liegt die Summe darüber, die Angaben noch einmal prüfen. Jede Anpassung bekommt einen Satz, den der Eigentümer versteht, z. B. „Dach und Fassade im Original, Energieklasse E“.

### 3. Erzeugen

```bash
python3 scripts/bewertung.py objekte/<kurzname>.json     # PDF + HTML + Rechenweg (JSON)
python3 scripts/webseite.py  objekte/<kurzname>.json     # Webseite, legt das PDF als Download daneben
```

Ausgabe landet in `ausgabe/` (anderer Ort über `PAL_AUSGABE`). Die Konsole zeigt Bodenrichtwert, Wohnlage, Vergleichsgruppe, Anpassungen, Spanne und Startpreis.

### 4. Prüfen, bevor es rausgeht

- Bodenrichtwert gefunden und Nutzung beginnt mit `W` (Wohngebiet). Liegt die Adresse in einer Sonderfläche, die Hausnummer prüfen.
- Vergleichsgruppe hat mindestens 5 Verkäufe, sonst nimmt das Skript automatisch alle Wohnlagen und sagt das im Dokument.
- Ergebnis je m² Wohnfläche liegt innerhalb der Bezirksspanne (Seite 3, Diagramm). Liegt es außerhalb, Anpassungen prüfen.
- Bodenanteil (Seite 4) liegt bei Berliner Einfamilienhäusern meist zwischen 35 und 70 %.
- PDF hat genau 5 Seiten, nichts ragt in die Fußzeile. Seiten ansehen, z. B. mit `pdftoppm -png -r 80`.

### 5. Webseite teilen

`ausgabe/web/<kurzname>/` enthält `index.html` (alle Bilder eingebettet) und das PDF. Die Seite ist `noindex`. Weil Name und Adresse des Eigentümers darauf stehen, nur unter einem nicht erratbaren Pfad hochladen (z. B. `/marktwert/k7x2-kladow`), nie in ein öffentliches Verzeichnis mit Liste.

## Regeln für Text und Recht

- Nie „Höchstpreis“, „garantiert“ oder feste Verkaufsdauer versprechen.
- Das Dokument ist eine Marktwert-Einschätzung, kein Gutachten. Nie „Gutachten“, „Gutachter“ oder „Verkehrswert“ für das eigene Ergebnis verwenden. Der Hinweis auf Seite 5 bleibt immer drin.
- Der Gutachterausschuss gibt keine einzelnen Kaufverträge heraus, nur Mittel und Spannen je Gruppe. Deshalb immer „Vergleichsgruppe mit n Verkäufen“, nie „echte Notarpreise aus Ihrer Straße“.
- Jede Zahl steht mit Quelle im Dokument. Kein Wappen und kein Anschein einer Zusammenarbeit mit dem Gutachterausschuss.
- Im Fließtext keine Sätze mit Doppelpunkt-Aufzählung, lieber zwei Sätze.

## Eigene Marke

Alles Markenspezifische steht in `marke.json` (Name, Firma, Adresse, Telefon, WhatsApp, E-Mail, Impressum, Datenschutz, Methodenname, Berater, Foto, Logos, drei Farben). Logos als PNG nach `assets/` legen (`logo_hell` auf dunklem Grund, `logo_dunkel` auf hellem). Ein Objekt darf `berater`, `berater_rolle` und `berater_foto` überschreiben, wenn ein Kollege den Lead betreut.

## Daten und Grenzen

- `scripts/marktdaten.py` enthält die Tabellen des Immobilienmarktberichts Berlin 2025/26 (S. 49–57, Lizenz dl-de/zero-2-0). Der nächste Bericht erscheint im Sommer 2027, dann die Tabellen tauschen.
- Bodenrichtwerte kommen live aus den WFS-Diensten `brw2026`, `brw2025`, `brw2024` auf `gdi.berlin.de`. Für den Stichtag 01.01.2027 in `BRW_LAYER` (scripts/bewertung.py) einen Eintrag ergänzen und den Layernamen per `GetCapabilities` prüfen.
- Wohnlage kommt aus dem Straßenverzeichnis zum Mietspiegel 2024 (`wohnlagenadr2024`) und dient als Näherung für die Lageklasse im Marktbericht.
- Nur Ein- und Zweifamilienhäuser, Doppelhaushälften und Reihenhäuser in Berlin. Eigentumswohnungen und Brandenburg deckt der Skill noch nicht ab.
- Ohne Hausnummer nimmt das Skript den Punkt der Straße und die häufigste Wohnlage der Straße.

## Rechenweg im Detail

1. Geschossfläche = Wohnfläche / 0,81 (amtlicher Mittelwert, S. 49)
2. Ausgangswert = Geschossfläche × Ø Kaufpreis je m² Geschossfläche der Vergleichsgruppe
3. Grundstück = (Grundstück − Ø Grundstück der Gruppe) × Bodenrichtwert, als Prozent vom Ausgangswert, höchstens ±8 %
4. Hausgröße = −25 % × relative Abweichung von der Ø Geschossfläche der Gruppe, höchstens ±5 %
5. Plus die Anpassungen aus dem Objekt
6. Mitte auf 5.000 € gerundet, Spanne ± `spanne_prozent` auf 5.000 € abgerundet bzw. aufgerundet
7. Startpreis = Mitte + 60 % des Wegs zur Obergrenze, liegt er bis 1,5 % über einer runden 50.000er-Grenze, dann 5.000 € unter dieser Grenze
