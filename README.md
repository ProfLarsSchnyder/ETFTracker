# ETFTracker

Persönliches ETF Research Dashboard mit Favoriten, Watchlist, ETF Radar und Vergleich.

## Stand

Die Oberfläche funktioniert bereits mit bewusst statischen Demo-Daten. Es werden keine privaten Depotwerte gespeichert.

## Bereiche

- Dashboard
- Meine ETFs
- ETF Radar
- Watchlist
- Vergleich

## Speicherung

Favoriten, Watchlist und Vergleichsauswahl werden nur lokal im Browser über `localStorage` gespeichert.

## Nächster Schritt

Eine Marktdaten API anbinden, damit Kurse und Performance automatisch aktualisiert werden. Der API Schlüssel soll später nicht im öffentlichen Frontend liegen, sondern über eine Serverless Function beziehungsweise eine sichere Umgebungsvariable verwendet werden.

## Hinweis

Der Opportunity Score ist ein Research- und Screening-Werkzeug und kein Kaufsignal oder eine Anlageempfehlung.
