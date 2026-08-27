#!/usr/bin/env python3
"""Build a diverse UCITS ETF candidate universe from the public etfdb catalogue.

The catalogue itself is not served to the browser. It is only used by the GitHub
Action to select a manageable research universe. Live price history still comes
from Yahoo Finance.
"""

import csv
import io
import math
import re
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta

CATALOG_URL = "https://raw.githubusercontent.com/albertored/etfdb/main/csv/basic_info.csv"
USER_AGENT = "Mozilla/5.0 ETFTracker/2.0"

CATEGORY_ORDER = [
    "Welt Aktien", "USA", "Europa", "Emerging Markets", "Schweiz", "Japan", "China", "Indien",
    "Small Caps", "Quality Factor", "Value Factor", "Momentum Factor", "Minimum Volatility", "Dividenden",
    "Technologie", "Künstliche Intelligenz", "Halbleiter", "Cybersecurity", "Robotik", "Cloud Computing",
    "Biotechnologie", "Gesundheit", "Clean Energy", "Nuclear", "Batterien & EV", "Lithium", "Kupfer",
    "Strategische Metalle", "Goldminen", "Wasser", "Infrastruktur", "Immobilien", "Defense", "Klima",
    "Weitere Aktien",
]


def _download_text(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8-sig")


def _num(value, default=None):
    try:
        number = float(str(value).strip())
        return number if math.isfinite(number) else default
    except Exception:
        return default


def _date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def _norm(value):
    value = (value or "").lower()
    value = re.sub(r"\b(usd|eur|gbp|chf|acc|dist|distributing|accumulating|hedged|unhedged)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def classify(row):
    text = f"{row.get('name','')} {row.get('index','')}".lower()

    rules = [
        ("Künstliche Intelligenz", ["artificial intelligence", "ai &", " ai ", "big data", "machine learning"]),
        ("Halbleiter", ["semiconductor", "semiconductors"]),
        ("Cybersecurity", ["cyber security", "cybersecurity", "digital security"]),
        ("Robotik", ["robotics", "automation", "automatisation"]),
        ("Cloud Computing", ["cloud computing", "cloud technology"]),
        ("Biotechnologie", ["biotech", "biotechnology", "genomics", "genomic"]),
        ("Gesundheit", ["healthcare", "health care", "medical", "ageing population", "aging population"]),
        ("Nuclear", ["uranium", "nuclear"]),
        ("Lithium", ["lithium"]),
        ("Kupfer", ["copper"]),
        ("Strategische Metalle", ["rare earth", "strategic metal", "critical metal", "critical mineral"]),
        ("Goldminen", ["gold miner", "gold mining", "gold producers"]),
        ("Batterien & EV", ["battery", "batteries", "electric vehicle", "future mobility"]),
        ("Clean Energy", ["clean energy", "renewable energy", "solar", "hydrogen", "energy transition"]),
        ("Defense", ["defence", "defense", "aerospace & defence", "aerospace and defense"]),
        ("Wasser", [" water ", "global water", "clean water"]),
        ("Infrastruktur", ["infrastructure", "smart city", "digital infrastructure"]),
        ("Immobilien", ["real estate", "reit", "property"]),
        ("Klima", ["climate", "decarbon", "low carbon", "carbon transition"]),
        ("Quality Factor", ["quality factor", "world quality", "usa quality", "quality dividend"]),
        ("Momentum Factor", ["momentum factor", "world momentum", "usa momentum"]),
        ("Value Factor", ["value factor", "enhanced value", "world value", "usa value"]),
        ("Minimum Volatility", ["minimum volatility", "min volatility", "minimum variance", "low volatility"]),
        ("Dividenden", ["dividend", "income equity", "high yield equity"]),
        ("Small Caps", ["small cap", "smallcap", "small-cap"]),
        ("Indien", [" india", "india ", "nifty"]),
        ("China", [" china", "china ", "csi 300", "msci china", "hang seng"]),
        ("Japan", [" japan", "japan ", "topix", "nikkei"]),
        ("Schweiz", ["switzerland", "swiss", "smi ", "spi "]),
        ("Emerging Markets", ["emerging market", "em markets", "msci em", "ftse emerging"]),
        ("Europa", ["europe", "euro stoxx", "stoxx europe", "msci emu", "eurozone"]),
        ("USA", ["s&p 500", "s&p500", "nasdaq 100", "nasdaq-100", "russell 1000", "msci usa", "usa equity", "us equity"]),
        ("Technologie", ["technology", "information tech", "digitalisation", "digitalization", "internet", "software"]),
        ("Welt Aktien", ["msci world", "ftse all-world", "ftse all world", "msci acwi", "global equity", "world equity"]),
    ]

    padded = f" {text} "
    for category, needles in rules:
        if any(needle in padded for needle in needles):
            return category
    return "Weitere Aktien"


def quality_score(row):
    size = _num(row.get("size"), 0) or 0
    ter = _num(row.get("ter"), 1.5)
    holdings = _num(row.get("number_of_holdings"), 0) or 0
    inception = _date(row.get("inception_date"))
    age_years = ((date.today() - inception).days / 365.25) if inception else 0

    # Large, inexpensive and seasoned funds get priority. The square/log transforms
    # stop mega funds from swallowing the whole universe.
    return (
        math.log10(size + 10) * 12
        - min(ter, 2.0) * 5
        + min(age_years, 15) * 0.35
        + min(math.log10(holdings + 1), 3) * 1.5
    )


def load_candidates(curated_isins):
    text = _download_text(CATALOG_URL)
    reader = csv.DictReader(io.StringIO(text))
    cutoff = date.today() - timedelta(days=365)
    candidates = []

    for row in reader:
        isin = (row.get("isin") or "").strip()
        name = (row.get("name") or "").strip()
        ticker = (row.get("ticker") or "").strip()
        if not isin or not name or not ticker or isin in curated_isins:
            continue
        if (row.get("asset_class") or "").strip().lower() != "equity":
            continue
        if "ucits" not in name.lower():
            continue
        strategy = (row.get("strategies") or "").lower()
        if "short" in strategy or "leverage" in strategy:
            continue
        inception = _date(row.get("inception_date"))
        if not inception or inception > cutoff:
            continue
        ter = _num(row.get("ter"))
        size = _num(row.get("size"), 0) or 0
        if ter is None or ter > 0.90:
            continue
        if size < 40:
            continue

        row = dict(row)
        row["category"] = classify(row)
        row["quality_score"] = quality_score(row)
        candidates.append(row)

    return candidates


def select_diverse(candidates, target):
    groups = defaultdict(list)
    for row in candidates:
        groups[row["category"]].append(row)
    for rows in groups.values():
        rows.sort(key=lambda r: r["quality_score"], reverse=True)

    selected = []
    seen_funds = set()

    def add(row):
        key = (
            _norm(row.get("fund_provider")),
            _norm(row.get("index")) or _norm(row.get("name")),
        )
        if key in seen_funds:
            return False
        seen_funds.add(key)
        selected.append(row)
        return True

    # First pass gives the radar breadth: up to two good funds per category.
    for category in CATEGORY_ORDER:
        added = 0
        for row in groups.get(category, []):
            if add(row):
                added += 1
            if added >= 2 or len(selected) >= target:
                break
        if len(selected) >= target:
            return selected

    # Second pass allows up to five per category, favouring category leaders.
    per_category = defaultdict(int)
    for row in selected:
        per_category[row["category"]] += 1
    pool = sorted(candidates, key=lambda r: r["quality_score"], reverse=True)
    for row in pool:
        if len(selected) >= target:
            break
        category = row["category"]
        if per_category[category] >= 5:
            continue
        if add(row):
            per_category[category] += 1

    # Last fill if the caps left space.
    for row in pool:
        if len(selected) >= target:
            break
        add(row)

    return selected


def discover_from_catalog(config, previous_payload):
    discovery = config.get("discovery") or {}
    target_total = int(discovery.get("targetTotal", 100))
    curated = config.get("etfs", [])
    target_auto = max(0, target_total - len(curated))

    cached = []
    for item in (previous_payload or {}).get("items", []):
        if item.get("autoDiscovered") and item.get("yahooSymbol"):
            cached.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "category": item.get("category") or "Weitere Aktien",
                "provider": item.get("provider"),
                "ter": item.get("ter"),
                "isin": item.get("isin"),
                "catalogTicker": item.get("catalogTicker") or item.get("displaySymbol") or item.get("symbol"),
                "yahooSymbol": item.get("yahooSymbol"),
                "displaySymbol": item.get("displaySymbol") or item.get("symbol"),
                "size": item.get("size"),
                "index": item.get("index"),
                "autoDiscovered": True,
            })

    by_isin = {item.get("isin"): item for item in cached if item.get("isin")}
    if len(by_isin) >= target_auto:
        return list(by_isin.values())[:target_auto]

    curated_isins = {item.get("isin") for item in curated if item.get("isin")}
    candidates = load_candidates(curated_isins | set(by_isin))
    chosen = select_diverse(candidates, target_auto - len(by_isin))

    for row in chosen:
        isin = row["isin"].strip()
        clean_id = re.sub(r"[^a-z0-9]+", "-", isin.lower()).strip("-")
        by_isin[isin] = {
            "id": f"auto-{clean_id}",
            "name": row.get("name"),
            "category": row.get("category") or "Weitere Aktien",
            "provider": row.get("fund_provider"),
            "ter": _num(row.get("ter")),
            "isin": isin,
            "catalogTicker": row.get("ticker"),
            "displaySymbol": row.get("ticker"),
            "size": _num(row.get("size")),
            "index": row.get("index"),
            "autoDiscovered": True,
        }

    return list(by_isin.values())[:target_auto]
