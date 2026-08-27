#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "scripts" / "update_market_data.py"
text = path.read_text(encoding="utf-8")

import_line = "from pathlib import Path\n"
if "from catalog_discovery import discover_from_catalog" not in text:
    text = text.replace(import_line, import_line + "from catalog_discovery import discover_from_catalog\n")

old_start = '''def discover_etfs(config, previous_payload):\n    discovery = config.get("discovery") or {}\n    if not discovery.get("enabled", False):\n        return []\n\n    target_total = int(discovery.get("targetTotal", 100))'''
new_start = '''def discover_etfs(config, previous_payload):\n    discovery = config.get("discovery") or {}\n    if not discovery.get("enabled", False):\n        return []\n    if discovery.get("catalogSource", "etfdb") == "etfdb":\n        return discover_from_catalog(config, previous_payload)\n\n    target_total = int(discovery.get("targetTotal", 100))'''
if old_start in text:
    text = text.replace(old_start, new_start)

marker = '''    candidates = []\n    queries = []\n'''
insert = '''    ticker = item.get("catalogTicker")\n    if ticker:\n        ticker = str(ticker).strip()\n        ticker_candidates = []\n        if "." in ticker:\n            ticker_candidates.append(ticker)\n        ticker_candidates.extend([ticker + suffix for suffix in EUROPE_SUFFIXES])\n        ticker_candidates.append(ticker)\n        for candidate in ticker_candidates:\n            try:\n                candidate_result = chart(candidate, "1mo", "1d")\n                meta = candidate_result.get("meta", {})\n                instrument = str(meta.get("instrumentType") or "").upper()\n                if instrument and instrument not in {"ETF", "MUTUALFUND"}:\n                    continue\n                return candidate\n            except Exception:\n                continue\n\n    candidates = []\n    queries = []\n'''
if marker in text and "ticker_candidates = []" not in text:
    text = text.replace(marker, insert, 1)

old_fields = '''        "autoDiscovered": bool(config_item.get("autoDiscovered")),\n        "yahooSymbol": symbol,'''
new_fields = '''        "autoDiscovered": bool(config_item.get("autoDiscovered")),\n        "catalogTicker": config_item.get("catalogTicker"),\n        "size": config_item.get("size"),\n        "index": config_item.get("index"),\n        "yahooSymbol": symbol,'''
if old_fields in text:
    text = text.replace(old_fields, new_fields)

path.write_text(text, encoding="utf-8")
print("Catalogue discovery wired into updater")
