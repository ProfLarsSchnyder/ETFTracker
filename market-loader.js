(async function loadMarketDataAndStart() {
  const pill = document.querySelector('.status-pill');
  const sidebarNote = document.querySelector('.sidebar-note');

  function setStatus(text, state) {
    if (!pill) return;
    const dotClass = state === 'live' ? 'status-dot status-dot-live' : 'status-dot';
    pill.innerHTML = `<span class="${dotClass}"></span>${text}`;
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = `${src}?v=${Date.now()}`;
      script.onload = resolve;
      script.onerror = reject;
      document.body.appendChild(script);
    });
  }

  function genericReason(item) {
    if (item.reason) return item.reason;
    if (item.trend === 'Early Trend') return 'Erste Anzeichen eines neuen Aufwärtstrends. Der Trend ist noch weniger bestätigt als bei Mid Trend.';
    if (item.trend === 'Mid Trend') return 'Etablierter positiver Trend, aktuell ohne extreme technische Überdehnung.';
    if (item.trend === 'Extended') return 'Starker Trend, der bereits weit gelaufen ist. Das Rückschlagrisiko ist erhöht.';
    return 'Aktuell technisch schwache oder noch nicht bestätigte Trendstruktur.';
  }

  setStatus('Marktdaten werden geladen…', 'loading');

  try {
    const response = await fetch(`market-data.json?t=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const liveItems = Array.isArray(payload.items) ? payload.items : [];
    const existingById = new Map((window.ETF_DATA || []).map((item) => [item.id, item]));

    const liveFields = [
      'name', 'symbol', 'displaySymbol', 'isin', 'category', 'provider', 'ter', 'price', 'currency',
      'perf1h', 'perfDay', 'perfWeek', 'perfMonth', 'perf3m', 'perf6m', 'perfYtd', 'perf1y',
      'perf3y', 'perf5y', 'high52', 'low52', 'sma50', 'sma200', 'volatility', 'maxDrawdown',
      'trend', 'yahooSymbol', 'exchangeName', 'marketState', 'asOf', 'autoDiscovered'
    ];

    let mergedCount = 0;
    let appendedCount = 0;

    liveItems.forEach((live) => {
      let etf = existingById.get(live.id);
      if (!etf) {
        etf = {
          id: live.id,
          name: live.name || live.yahooSymbol || live.id,
          symbol: live.displaySymbol || live.symbol || (live.yahooSymbol ? live.yahooSymbol.split('.')[0] : live.id),
          isin: live.isin || '',
          category: live.category || 'Weitere',
          provider: live.provider || '',
          ter: live.ter ?? null,
          reason: genericReason(live)
        };
        window.ETF_DATA.push(etf);
        existingById.set(etf.id, etf);
        appendedCount += 1;
      }

      liveFields.forEach((field) => {
        if (live[field] !== undefined) etf[field] = live[field];
      });
      etf.symbol = live.displaySymbol || live.symbol || etf.symbol;
      etf.reason = genericReason(live);
      etf.marketDataLive = true;
      mergedCount += 1;
    });

    window.ETF_MARKET_STATUS = payload;
    const generated = payload.generatedAt ? new Date(payload.generatedAt) : null;
    const timeLabel = generated && !Number.isNaN(generated.getTime())
      ? generated.toLocaleString('de-CH', { dateStyle: 'short', timeStyle: 'short' })
      : 'aktuell';

    if (mergedCount > 0) {
      setStatus(`${mergedCount} ETFs live · ${timeLabel}`, 'live');
      if (sidebarNote) {
        const autoCount = Number(payload.autoDiscoveredCount || appendedCount || 0);
        sidebarNote.innerHTML = `
          <strong>Live ETF Radar</strong>
          <p>${mergedCount} ETFs werden kostenlos automatisiert analysiert, davon ${autoCount} automatisch entdeckte UCITS ETFs. Quelle: Yahoo Finance. Letztes Update: ${timeLabel}.</p>`;
      }
    } else {
      setStatus('Demo Daten · Live-Update ausstehend', 'demo');
    }
  } catch (error) {
    console.warn('Live-Marktdaten konnten nicht geladen werden, Demo-Daten bleiben aktiv:', error);
    setStatus('Demo Daten · Live-Daten nicht verfügbar', 'demo');
  }

  try {
    await loadScript('app.js');
    await loadScript('help.js');
  } catch (error) {
    console.error('ETF Tracker konnte nicht vollständig gestartet werden:', error);
  }
})();
