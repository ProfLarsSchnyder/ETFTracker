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

  setStatus('Marktdaten werden geladen…', 'loading');

  try {
    const response = await fetch(`market-data.json?t=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const liveItems = Array.isArray(payload.items) ? payload.items : [];
    const liveById = new Map(liveItems.map((item) => [item.id, item]));

    let mergedCount = 0;
    (window.ETF_DATA || []).forEach((etf) => {
      const live = liveById.get(etf.id);
      if (!live) return;
      const liveFields = [
        'price', 'currency', 'perf1h', 'perfDay', 'perfWeek', 'perfMonth', 'perf3m',
        'perf6m', 'perfYtd', 'perf1y', 'perf3y', 'perf5y', 'high52', 'low52',
        'sma50', 'sma200', 'volatility', 'maxDrawdown', 'trend', 'yahooSymbol',
        'exchangeName', 'marketState', 'asOf'
      ];
      liveFields.forEach((field) => {
        if (live[field] !== null && live[field] !== undefined) etf[field] = live[field];
      });
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
        sidebarNote.innerHTML = `
          <strong>Live Marktdaten</strong>
          <p>Kurse und Renditen werden kostenlos automatisiert aktualisiert. Quelle: Yahoo Finance. Letztes Update: ${timeLabel}.</p>`;
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
