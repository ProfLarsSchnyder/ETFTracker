# ETFTracker

Persönliches ETF Research Dashboard mit Favoriten, Watchlist, ETF Radar und Vergleich.

## Stand

Die Oberfläche nutzt automatisch aktualisierte Marktdaten, sofern diese verfügbar sind. Es werden keine privaten Depotwerte gespeichert. Falls das automatische Update einmal ausfällt, bleiben die bisherigen Demo-Daten als Fallback erhalten.

## Bereiche

- Dashboard
- Meine ETFs
- ETF Radar
- Watchlist
- Vergleich

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

## Automatische Aktualisierung

Workflow: `.github/workflows/update-market-data.yml`

Updater: `scripts/update_market_data.py`

Konfiguration der ETF-Listings: `market-config.json`

Der Workflow läuft stündlich und kann in GitHub Actions zusätzlich manuell gestartet werden.

## Speicherung

Favoriten, Watchlist und Vergleichsauswahl werden nur lokal im Browser über `localStorage` gespeichert.

## Hinweis zur Datenquelle

Die verwendeten Yahoo-Finance-Endpunkte benötigen keinen API-Key, sind aber keine garantierte offizielle Entwickler-API. Deshalb ist die Datenabfrage so gebaut, dass die Website bei einem Ausfall weiterhin funktioniert. Für ein späteres öffentliches oder kommerzielles Produkt sollte die Datenlizenzierung separat geprüft werden.

Der Opportunity Score ist ein Research- und Screening-Werkzeug und kein Kaufsignal oder eine Anlageempfehlung.
