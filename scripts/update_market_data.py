#!/usr/bin/env python3
import json
import math
import re
import statistics
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "market-config.json"
OUTPUT_PATH = ROOT / "market-data.json"
USER_AGENT = "Mozilla/5.0 ETFTracker/2.0"
EUROPE_SUFFIXES = [".SW", ".DE", ".L", ".AS", ".MI", ".PA", ".SG", ".F"]
EXCLUDED_DISCOVERY_TERMS = ["leveraged", "inverse", "ultrashort", "2x", "3x", "short daily", "daily short"]


def http_json(url, attempts=3):
    last_error = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json,text/plain,*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_error


def yahoo_search(query, count=20):
    url = "https://query1.finance.yahoo.com/v1/finance/search?" + urllib.parse.urlencode(
        {"q": query, "quotesCount": count, "newsCount": 0, "enableFuzzyQuery": "false"}
    )
    payload = http_json(url)
    return payload.get("quotes", [])


def chart(symbol, range_value, interval):
    encoded = urllib.parse.quote(symbol, safe="")
    query = urllib.parse.urlencode(
        {
            "range": range_value,
            "interval": interval,
            "includeAdjustedClose": "true",
            "events": "div,splits",
        }
    )
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?{query}"
    payload = http_json(url)
    chart_data = payload.get("chart", {})
    if chart_data.get("error"):
        raise RuntimeError(str(chart_data["error"]))
    results = chart_data.get("result") or []
    if not results:
        raise RuntimeError(f"Keine Kursdaten für {symbol}")
    return results[0]


def resolve_symbol(item, cached_symbol=None):
    for preferred in [item.get("yahooSymbol"), cached_symbol]:
        if preferred:
            try:
                chart(preferred, "1mo", "1d")
                return preferred
            except Exception:
                pass

    candidates = []
    queries = []
    if item.get("isin"):
        queries.append(item["isin"])
    if item.get("name"):
        queries.append(item["name"])
    queries.extend(item.get("searchQueries", []))

    for query in queries:
        try:
            candidates.extend(yahoo_search(query))
        except Exception:
            continue

    seen = set()
    scored = []
    for quote in candidates:
        symbol = quote.get("symbol")
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        quote_type = (quote.get("quoteType") or "").upper()
        if quote_type not in {"ETF", "MUTUALFUND"}:
            continue
        name = f"{quote.get('longname','')} {quote.get('shortname','')}".lower()
        score = 0
        tokens = [token for token in re.findall(r"[a-z0-9]+", item.get("name", "").lower()) if len(token) > 4]
        score += sum(2 for token in tokens if token in name)
        if "ucits" in name:
            score += 8
        for rank, suffix in enumerate(EUROPE_SUFFIXES):
            if symbol.endswith(suffix):
                score += 10 - rank * 0.5
                break
        scored.append((score, symbol))

    scored.sort(reverse=True)
    for _, symbol in scored:
        try:
            chart(symbol, "1mo", "1d")
            return symbol
        except Exception:
            continue
    raise RuntimeError(f"Kein Yahoo-Symbol gefunden für {item.get('name')}")


def quote_name(quote):
    return (quote.get("longname") or quote.get("shortname") or quote.get("symbol") or "").strip()


def normalize_name(name):
    value = name.lower()
    value = re.sub(r"\b(usd|eur|gbp|chf|acc|dist|distributing|accumulating)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def discover_etfs(config, previous_payload):
    discovery = config.get("discovery") or {}
    if not discovery.get("enabled", False):
        return []

    target_total = int(discovery.get("targetTotal", 100))
    base_count = len(config.get("etfs", []))
    target_auto = max(0, target_total - base_count)

    cached = []
    for item in (previous_payload or {}).get("items", []):
        if item.get("autoDiscovered") and item.get("yahooSymbol"):
            cached.append({
                "id": item.get("id"),
                "name": item.get("name") or item.get("yahooSymbol"),
                "category": item.get("category") or "Weitere",
                "provider": item.get("provider"),
                "ter": item.get("ter"),
                "isin": item.get("isin"),
                "yahooSymbol": item.get("yahooSymbol"),
                "displaySymbol": item.get("displaySymbol") or item.get("symbol"),
                "autoDiscovered": True,
            })

    by_symbol = {item["yahooSymbol"]: item for item in cached}
    seen_names = {normalize_name(item.get("name", "")) for item in cached}

    if len(by_symbol) >= target_auto:
        return list(by_symbol.values())[:target_auto]

    for query_cfg in discovery.get("queries", []):
        if len(by_symbol) >= target_auto:
            break
        query = query_cfg.get("query") if isinstance(query_cfg, dict) else str(query_cfg)
        category = query_cfg.get("category", "Weitere") if isinstance(query_cfg, dict) else "Weitere"
        if not query:
            continue
        try:
            quotes = yahoo_search(query, count=int(discovery.get("quotesPerQuery", 20)))
        except Exception as exc:
            print(f"Discovery-Fehler {query}: {exc}")
            continue

        for quote in quotes:
            if len(by_symbol) >= target_auto:
                break
            if (quote.get("quoteType") or "").upper() != "ETF":
                continue
            symbol = quote.get("symbol")
            name = quote_name(quote)
            if not symbol or not name:
                continue
            if not any(symbol.endswith(suffix) for suffix in EUROPE_SUFFIXES):
                continue
            lower_name = name.lower()
            if any(term in lower_name for term in EXCLUDED_DISCOVERY_TERMS):
                continue
            normalized = normalize_name(name)
            if symbol in by_symbol or normalized in seen_names:
                continue
            try:
                candidate_chart = chart(symbol, "1y", "1d")
                if len(series_from_chart(candidate_chart, prefer_adjusted=True)) < 60:
                    continue
            except Exception:
                continue

            clean_id = re.sub(r"[^a-z0-9]+", "-", symbol.lower()).strip("-")
            by_symbol[symbol] = {
                "id": f"auto-{clean_id}",
                "name": name,
                "category": category,
                "provider": None,
                "ter": None,
                "isin": None,
                "yahooSymbol": symbol,
                "displaySymbol": symbol.split(".")[0],
                "autoDiscovered": True,
            }
            seen_names.add(normalized)
        time.sleep(0.2)

    return list(by_symbol.values())[:target_auto]


def series_from_chart(result, prefer_adjusted=True):
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    closes = []
    if prefer_adjusted:
        adj = indicators.get("adjclose") or []
        if adj and adj[0].get("adjclose"):
            closes = adj[0]["adjclose"]
    if not closes:
        quote = indicators.get("quote") or []
        closes = quote[0].get("close", []) if quote else []

    points = []
    for ts, value in zip(timestamps, closes):
        if value is None:
            continue
        try:
            value = float(value)
            if math.isfinite(value) and value > 0:
                points.append((int(ts), value))
        except Exception:
            continue
    return points


def pct_change(current, previous):
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1.0) * 100.0


def value_at_or_before(points, target_ts):
    selected = None
    for ts, value in points:
        if ts <= target_ts:
            selected = value
        else:
            break
    return selected


def performance_for_days(points, days):
    if not points:
        return None
    last_ts, last_value = points[-1]
    target = last_ts - int(days * 86400)
    old = value_at_or_before(points, target)
    return pct_change(last_value, old)


def performance_ytd(points):
    if not points:
        return None
    last_ts, last_value = points[-1]
    dt = datetime.fromtimestamp(last_ts, tz=timezone.utc)
    jan1 = datetime(dt.year, 1, 1, tzinfo=timezone.utc).timestamp()
    old = value_at_or_before(points, int(jan1))
    if old is None:
        for ts, value in points:
            if ts >= jan1:
                old = value
                break
    return pct_change(last_value, old)


def sma(points, window):
    values = [value for _, value in points[-window:]]
    if len(values) < window:
        return None
    return sum(values) / len(values)


def annualized_volatility(points, lookback=252):
    values = [value for _, value in points[-(lookback + 1):]]
    if len(values) < 30:
        return None
    returns = []
    for prev, cur in zip(values, values[1:]):
        if prev > 0 and cur > 0:
            returns.append(math.log(cur / prev))
    if len(returns) < 20:
        return None
    return statistics.stdev(returns) * math.sqrt(252) * 100.0


def max_drawdown(points):
    peak = None
    worst = 0.0
    for _, value in points:
        if peak is None or value > peak:
            peak = value
        if peak and peak > 0:
            worst = min(worst, (value / peak - 1.0) * 100.0)
    return worst


def infer_trend(price, sma50_value, sma200_value, perf3m, perf6m, distance_sma200):
    if not price or not sma200_value:
        return "Weak"
    if price < sma200_value:
        return "Weak"
    if distance_sma200 is not None and distance_sma200 > 25:
        return "Extended"
    if sma50_value and sma50_value > sma200_value:
        if (perf3m or 0) > 0 and (perf6m or 0) > 0:
            return "Mid Trend"
        return "Early Trend"
    if (perf3m or 0) > 0:
        return "Early Trend"
    return "Weak"


def round_or_none(value, digits=4):
    if value is None:
        return None
    try:
        value = float(value)
        if not math.isfinite(value):
            return None
        return round(value, digits)
    except Exception:
        return None


def dynamic_reason(trend, perf3m, perf1y, distance_sma200, volatility):
    if trend == "Early Trend":
        base = "Frühe positive Trendstruktur"
    elif trend == "Mid Trend":
        base = "Etablierter positiver Trend"
    elif trend == "Extended":
        base = "Starker, aber bereits überdehnter Trend"
    else:
        base = "Aktuell technisch schwache Trendstruktur"
    details = []
    if perf3m is not None:
        details.append(f"3M {perf3m:+.1f} %")
    if perf1y is not None:
        details.append(f"1J {perf1y:+.1f} %")
    if distance_sma200 is not None:
        details.append(f"SMA200 {distance_sma200:+.1f} %")
    if volatility is not None:
        details.append(f"Volatilität {volatility:.1f} %")
    return base + (". " + ", ".join(details) + "." if details else ".")


def build_item(config_item, cached_symbol=None):
    symbol = resolve_symbol(config_item, cached_symbol=cached_symbol)
    daily_result = chart(symbol, "5y", "1d")
    intraday_result = chart(symbol, "5d", "60m")

    daily = series_from_chart(daily_result, prefer_adjusted=True)
    intraday = series_from_chart(intraday_result, prefer_adjusted=False)
    if len(daily) < 30:
        raise RuntimeError(f"Zu wenig Tagesdaten für {symbol}")

    meta = daily_result.get("meta", {})
    last_daily_ts, _ = daily[-1]
    current_ts, current_price = (intraday[-1] if intraday else daily[-1])

    perf_1h = pct_change(intraday[-1][1], intraday[-2][1]) if len(intraday) >= 2 else None
    perf_day = pct_change(daily[-1][1], daily[-2][1]) if len(daily) >= 2 else None
    perf_week = performance_for_days(daily, 7)
    perf_month = performance_for_days(daily, 30)
    perf_3m = performance_for_days(daily, 91)
    perf_6m = performance_for_days(daily, 182)
    perf_1y = performance_for_days(daily, 365)
    perf_3y = performance_for_days(daily, 365 * 3)
    perf_5y = performance_for_days(daily, 365 * 5)

    one_year_cutoff = last_daily_ts - 365 * 86400
    one_year_values = [value for ts, value in daily if ts >= one_year_cutoff]
    high52 = max(one_year_values) if one_year_values else max(value for _, value in daily)
    low52 = min(one_year_values) if one_year_values else min(value for _, value in daily)

    sma50_value = sma(daily, 50)
    sma200_value = sma(daily, 200)
    distance_sma200 = pct_change(current_price, sma200_value) if sma200_value else None
    volatility = annualized_volatility(daily)
    trend = infer_trend(current_price, sma50_value, sma200_value, perf_3m, perf_6m, distance_sma200)

    return {
        "id": config_item["id"],
        "name": config_item.get("name") or meta.get("longName") or symbol,
        "symbol": config_item.get("displaySymbol") or symbol.split(".")[0],
        "displaySymbol": config_item.get("displaySymbol") or symbol.split(".")[0],
        "isin": config_item.get("isin"),
        "category": config_item.get("category") or "Weitere",
        "provider": config_item.get("provider"),
        "ter": config_item.get("ter"),
        "autoDiscovered": bool(config_item.get("autoDiscovered")),
        "yahooSymbol": symbol,
        "price": round_or_none(current_price),
        "currency": meta.get("currency"),
        "exchangeName": meta.get("exchangeName") or meta.get("fullExchangeName"),
        "marketState": meta.get("marketState"),
        "asOf": datetime.fromtimestamp(current_ts, tz=timezone.utc).isoformat(),
        "perf1h": round_or_none(perf_1h),
        "perfDay": round_or_none(perf_day),
        "perfWeek": round_or_none(perf_week),
        "perfMonth": round_or_none(perf_month),
        "perf3m": round_or_none(perf_3m),
        "perf6m": round_or_none(perf_6m),
        "perfYtd": round_or_none(performance_ytd(daily)),
        "perf1y": round_or_none(perf_1y),
        "perf3y": round_or_none(perf_3y),
        "perf5y": round_or_none(perf_5y),
        "high52": round_or_none(high52),
        "low52": round_or_none(low52),
        "sma50": round_or_none(sma50_value),
        "sma200": round_or_none(sma200_value),
        "volatility": round_or_none(volatility, 3),
        "maxDrawdown": round_or_none(max_drawdown(daily), 3),
        "trend": trend,
        "reason": config_item.get("reason") or dynamic_reason(trend, perf_3m, perf_1y, distance_sma200, volatility),
    }


def load_previous():
    try:
        if OUTPUT_PATH.exists():
            return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    previous = load_previous()
    previous_by_id = {item.get("id"): item for item in previous.get("items", []) if item.get("id")}

    config_items = list(config.get("etfs", []))
    auto_items = discover_etfs(config, previous)
    all_items = config_items + auto_items

    print(f"ETF-Universum: {len(all_items)} ({len(config_items)} kuratiert, {len(auto_items)} automatisch entdeckt)")

    items = []
    errors = []
    for index, config_item in enumerate(all_items, start=1):
        try:
            cached_symbol = (previous_by_id.get(config_item.get("id")) or {}).get("yahooSymbol")
            result = build_item(config_item, cached_symbol=cached_symbol)
            items.append(result)
            print(f"OK {index}/{len(all_items)} {config_item['id']}: {result['yahooSymbol']}")
        except Exception as exc:
            errors.append({"id": config_item.get("id"), "name": config_item.get("name"), "error": str(exc)})
            print(f"FEHLER {index}/{len(all_items)} {config_item.get('id')}: {exc}")
        time.sleep(0.18)

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance chart/search endpoints",
        "sourceType": "keyless-free",
        "targetUniverse": (config.get("discovery") or {}).get("targetTotal", len(config_items)),
        "successCount": len(items),
        "failedCount": len(errors),
        "curatedCount": len(config_items),
        "autoDiscoveredCount": len([item for item in items if item.get("autoDiscovered")]),
        "items": items,
        "errors": errors,
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Geschrieben: {OUTPUT_PATH} ({len(items)} erfolgreich, {len(errors)} Fehler)")

    if not items:
        raise SystemExit("Keine Marktdaten konnten geladen werden.")


if __name__ == "__main__":
    main()
