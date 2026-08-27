#!/usr/bin/env python3
import json
import math
import statistics
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "market-config.json"
OUTPUT_PATH = ROOT / "market-data.json"
USER_AGENT = "Mozilla/5.0 ETFTracker/1.0"


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
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_error


def yahoo_search(query):
    url = "https://query1.finance.yahoo.com/v1/finance/search?" + urllib.parse.urlencode(
        {"q": query, "quotesCount": 12, "newsCount": 0, "enableFuzzyQuery": "false"}
    )
    payload = http_json(url)
    return payload.get("quotes", [])


def resolve_symbol(item):
    preferred = item.get("yahooSymbol")
    if preferred:
        try:
            chart(preferred, "1mo", "1d")
            return preferred
        except Exception:
            pass

    candidates = []
    for query in [item.get("isin", ""), item.get("name", "")]:
        if not query:
            continue
        try:
            candidates.extend(yahoo_search(query))
        except Exception:
            continue

    preferred_suffixes = [".SW", ".DE", ".L", ".AS", ".MI", ".PA", ".SG", ".F"]
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
        if item.get("isin", "").lower() in name:
            score += 50
        tokens = [token for token in item.get("name", "").lower().replace("&", " ").split() if len(token) > 4]
        score += sum(1 for token in tokens if token in name)
        for rank, suffix in enumerate(preferred_suffixes):
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
            dd = (value / peak - 1.0) * 100.0
            worst = min(worst, dd)
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


def build_item(config_item):
    symbol = resolve_symbol(config_item)
    daily_result = chart(symbol, "5y", "1d")
    intraday_result = chart(symbol, "5d", "60m")

    daily = series_from_chart(daily_result, prefer_adjusted=True)
    intraday = series_from_chart(intraday_result, prefer_adjusted=False)
    if len(daily) < 30:
        raise RuntimeError(f"Zu wenig Tagesdaten für {symbol}")

    meta = daily_result.get("meta", {})
    last_daily_ts, last_daily = daily[-1]
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
    trend = infer_trend(current_price, sma50_value, sma200_value, perf_3m, perf_6m, distance_sma200)

    return {
        "id": config_item["id"],
        "isin": config_item.get("isin"),
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
        "volatility": round_or_none(annualized_volatility(daily), 3),
        "maxDrawdown": round_or_none(max_drawdown(daily), 3),
        "trend": trend,
    }


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    items = []
    errors = []

    for config_item in config.get("etfs", []):
        try:
            result = build_item(config_item)
            items.append(result)
            print(f"OK {config_item['id']}: {result['yahooSymbol']}")
        except Exception as exc:
            errors.append({"id": config_item.get("id"), "error": str(exc)})
            print(f"FEHLER {config_item.get('id')}: {exc}")
        time.sleep(0.35)

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance chart endpoints",
        "sourceType": "keyless-free",
        "successCount": len(items),
        "failedCount": len(errors),
        "items": items,
        "errors": errors,
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Geschrieben: {OUTPUT_PATH} ({len(items)} erfolgreich, {len(errors)} Fehler)")

    if not items:
        raise SystemExit("Keine Marktdaten konnten geladen werden.")


if __name__ == "__main__":
    main()
