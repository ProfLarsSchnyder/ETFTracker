# ETFTracker

Persönliches ETF Research Dashboard mit Favoriten, Watchlist, ETF Radar und Vergleich.

## Stand

Die Oberfläche nutzt automatisch aktualisierte Marktdaten, sofern diese verfügbar sind. Es werden keine privaten Depotwerte gespeichert. Falls das automatische Update einmal ausfällt, bleiben die zuletzt verfügbaren Daten beziehungsweise Demo-Daten als Fallback erhalten.

## Bereiche

- Dashboard
- Meine ETFs
- ETF Radar
- Watchlist
- Vergleich

## ETF Radar

Der Radar ist auf ein Research-Universum von rund 100 europäischen UCITS-Aktien-ETFs ausgelegt. 15 ETFs sind bewusst kuratiert, weitere ETFs werden automatisch aus einem öffentlichen europäischen ETF-Katalog ausgewählt. Dabei werden unter anderem Fondsgrösse, TER, Alter des Fonds, Long-only-Strategie und thematische Vielfalt berücksichtigt. Short- und Leveraged-Produkte werden ausgeschlossen.

Die automatisch entdeckten ETFs werden Kategorien wie Welt Aktien, USA, Europa, Emerging Markets, Faktoren, Technologie, KI, Halbleiter, Cybersecurity, Robotik, Biotechnologie, Gesundheit, Clean Energy, Nuclear, Rohstoffe, Infrastruktur, Immobilien oder Defense zugeordnet. Der Radar kann durchsucht, gefiltert und nach mehreren Kennzahlen sortiert werden.

## Marktdaten

Die Marktdaten werden ohne kostenpflichtiges Abo über öffentliche Yahoo-Finance-Chart-Endpunkte abgerufen. Ein GitHub-Actions-Workflow aktualisiert `market-data.json` stündlich.

Aus den Kursreihen werden unter anderem selbst berechnet:

- 1 Stunde
- Heute
- 1 Woche
- 1 Monat
- 3 Monate
- 6 Monate
- YTD
- 1 Jahr
- 3 Jahre
- 5 Jahre
- 52-Wochen-Hoch und -Tief
- SMA 50 und SMA 200
- annualisierte Volatilität
- maximaler Drawdown
- Trendphase

Der Opportunity Score wird anschliessend im Browser aus diesen Kennzahlen neu berechnet. Die Score-Aufschlüsselung zeigt transparent, wie die Punkte zustande kommen.

## Kostenlose ETF-Katalogquelle

Für die automatische Auswahl zusätzlicher europäischer ETFs verwendet der GitHub-Workflow den öffentlichen `etfdb`-Katalog von albertored auf GitHub. Der Katalog enthält unter anderem ISIN, Ticker, Name, Anlageklasse, TER, Fondsgrösse, Auflagedatum, Index und Anbieter. Es wird nicht die gesamte Datenbank an den Browser ausgeliefert, sondern nur ein ausgewähltes Research-Universum mit den daraus benötigten Metadaten.

Quelle: `https://github.com/albertored/etfdb`

## Automatische Aktualisierung

Workflow: `.github/workflows/update-market-data.yml`

Updater: `scripts/update_market_data.py`

Katalogauswahl: `scripts/catalog_discovery.py`

Konfiguration: `market-config.json`

Der Workflow läuft stündlich und kann in GitHub Actions zusätzlich manuell gestartet werden.

## Speicherung

Favoriten, Watchlist und Vergleichsauswahl werden nur lokal im Browser über `localStorage` gespeichert.

## Hinweis zur Datenquelle

Die verwendeten Yahoo-Finance-Endpunkte benötigen keinen API-Key, sind aber keine garantierte offizielle Entwickler-API. Deshalb ist die Datenabfrage so gebaut, dass die Website bei einem Ausfall weiterhin funktioniert. Für ein späteres kommerzielles Produkt sollte die Datenlizenzierung separat geprüft werden.

Der Opportunity Score ist ein Research- und Screening-Werkzeug und kein Kaufsignal oder eine Anlageempfehlung.
