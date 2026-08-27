#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app_path = ROOT / "app.js"
index_path = ROOT / "index.html"

app = app_path.read_text(encoding="utf-8")
index = index_path.read_text(encoding="utf-8")

replacements = [
    (
        '''function formatNumber(value, digits = 2) {\n  return new Intl.NumberFormat("de-CH", {''',
        '''function formatNumber(value, digits = 2) {\n  if (value === null || value === undefined || Number.isNaN(Number(value))) return "–";\n  return new Intl.NumberFormat("de-CH", {'''
    ),
    (
        '''const terPoints = etf.ter <= 0.25 ? 3 : etf.ter <= 0.45 ? 2 : etf.ter <= 0.65 ? 1 : 0;''',
        '''const terPoints = etf.ter === null || etf.ter === undefined\n    ? 1.5\n    : etf.ter <= 0.25 ? 3 : etf.ter <= 0.45 ? 2 : etf.ter <= 0.65 ? 1 : 0;'''
    ),
    (
        '''TER (${formatNumber(etf.ter)} %). Bei jungen ETFs wird fehlende Historie neutral behandelt.''',
        '''TER (${etf.ter === null || etf.ter === undefined ? "nicht verfügbar" : `${formatNumber(etf.ter)} %`}). Fehlende TER oder junge Historie werden im Score neutral behandelt.'''
    ),
    (
        '''<td>${formatNumber(etf.ter)} %</td>''',
        '''<td>${etf.ter === null || etf.ter === undefined ? "–" : `${formatNumber(etf.ter)} %`}</td>'''
    ),
    (
        '''<strong>${formatNumber(etf.ter)} %</strong>''',
        '''<strong>${etf.ter === null || etf.ter === undefined ? "–" : `${formatNumber(etf.ter)} %`}</strong>'''
    ),
    (
        '''["TER", (e) => `${formatNumber(e.ter)} %`],''',
        '''["TER", (e) => e.ter === null || e.ter === undefined ? "–" : `${formatNumber(e.ter)} %`],'''
    ),
    (
        '''function renderRadar() {\n  const category = document.getElementById("categoryFilter")?.value || "all";\n  const trend = document.getElementById("trendFilter")?.value || "all";\n\n  const filtered = ETF_DATA\n    .filter((etf) => category === "all" || etf.category === category)\n    .filter((etf) => trend === "all" || etf.trend === trend)\n    .sort((a, b) => b.score - a.score);''',
        '''function renderRadar() {\n  const category = document.getElementById("categoryFilter")?.value || "all";\n  const trend = document.getElementById("trendFilter")?.value || "all";\n  const query = (document.getElementById("radarSearch")?.value || "").trim().toLowerCase();\n  const sortBy = document.getElementById("radarSort")?.value || "score";\n\n  const filtered = ETF_DATA\n    .filter((etf) => category === "all" || etf.category === category)\n    .filter((etf) => trend === "all" || etf.trend === trend)\n    .filter((etf) => !query || [etf.name, etf.symbol, etf.isin, etf.category, etf.provider]\n      .filter(Boolean)\n      .some((field) => String(field).toLowerCase().includes(query)))\n    .sort((a, b) => {\n      if (sortBy === "perf1y") return (b.perf1y ?? -9999) - (a.perf1y ?? -9999);\n      if (sortBy === "perf3m") return (b.perf3m ?? -9999) - (a.perf3m ?? -9999);\n      if (sortBy === "distanceHigh") return getDistanceFromHigh(b) - getDistanceFromHigh(a);\n      if (sortBy === "volatility") return (a.volatility ?? 9999) - (b.volatility ?? 9999);\n      return b.score - a.score;\n    });'''
    ),
    (
        '''document.getElementById("categoryFilter")?.addEventListener("change", renderRadar);\n  document.getElementById("trendFilter")?.addEventListener("change", renderRadar);''',
        '''document.getElementById("categoryFilter")?.addEventListener("change", renderRadar);\n  document.getElementById("trendFilter")?.addEventListener("change", renderRadar);\n  document.getElementById("radarSearch")?.addEventListener("input", renderRadar);\n  document.getElementById("radarSort")?.addEventListener("change", renderRadar);'''
    ),
]

for old, new in replacements:
    if old in app:
        app = app.replace(old, new)

old_toolbar = '''          <div class="toolbar-controls">\n            <select id="categoryFilter" aria-label="Kategorie filtern">\n              <option value="all">Alle Kategorien</option>\n            </select>\n            <select id="trendFilter" aria-label="Trendphase filtern">'''
new_toolbar = '''          <div class="toolbar-controls">\n            <input id="radarSearch" type="search" placeholder="ETF, Ticker oder Thema suchen" aria-label="ETF Radar durchsuchen" />\n            <select id="categoryFilter" aria-label="Kategorie filtern">\n              <option value="all">Alle Kategorien</option>\n            </select>\n            <select id="trendFilter" aria-label="Trendphase filtern">'''
if old_toolbar in index:
    index = index.replace(old_toolbar, new_toolbar)

old_after_trend = '''              <option value="Weak">Weak</option>\n            </select>\n          </div>'''
new_after_trend = '''              <option value="Weak">Weak</option>\n            </select>\n            <select id="radarSort" aria-label="ETF Radar sortieren">\n              <option value="score">Sortieren: Opportunity Score</option>\n              <option value="perf3m">Sortieren: 3 Monate</option>\n              <option value="perf1y">Sortieren: 1 Jahr</option>\n              <option value="distanceHigh">Sortieren: Nähe zum 52W Hoch</option>\n              <option value="volatility">Sortieren: niedrige Volatilität</option>\n            </select>\n          </div>'''
if old_after_trend in index and 'id="radarSort"' not in index:
    index = index.replace(old_after_trend, new_after_trend, 1)

app_path.write_text(app, encoding="utf-8")
index_path.write_text(index, encoding="utf-8")
print("UI patch applied")
