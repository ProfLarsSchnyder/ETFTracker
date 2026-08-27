const ETF_DATA = window.ETF_DATA || [];
const DEFAULTS = window.ETF_DEFAULTS || { favorites: [], watchlist: [] };

const STORAGE_KEYS = {
  favorites: "etfTrackerFavorites",
  watchlist: "etfTrackerWatchlist",
  compare: "etfTrackerCompare"
};

const state = {
  favorites: loadArray(STORAGE_KEYS.favorites, DEFAULTS.favorites),
  watchlist: loadArray(STORAGE_KEYS.watchlist, DEFAULTS.watchlist),
  compare: loadArray(STORAGE_KEYS.compare, [])
};

function loadArray(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return [...fallback];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [...fallback];
  } catch {
    return [...fallback];
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEYS.favorites, JSON.stringify(state.favorites));
  localStorage.setItem(STORAGE_KEYS.watchlist, JSON.stringify(state.watchlist));
  localStorage.setItem(STORAGE_KEYS.compare, JSON.stringify(state.compare));
}

function getEtf(id) {
  return ETF_DATA.find((etf) => etf.id === id);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function scale(value, min, max) {
  if (max === min) return 0;
  return clamp((value - min) / (max - min), 0, 1);
}

function round1(value) {
  return Math.round(value * 10) / 10;
}

function formatPct(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)} %`;
}

function hasHistory(value) {
  return typeof value === "number" && Number.isFinite(value) && value !== 0;
}

function formatHistoryPct(value) {
  return hasHistory(value) ? formatPct(value) : "–";
}

function formatNumber(value, digits = 2) {
  return new Intl.NumberFormat("de-CH", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  }).format(value);
}

function performanceClass(value) {
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "";
}

function getDistanceFromHigh(etf) {
  return ((etf.price / etf.high52) - 1) * 100;
}

function getDistanceFromSma200(etf) {
  return ((etf.price / etf.sma200) - 1) * 100;
}

function calculateOpportunityScore(etf) {
  const distanceHigh = getDistanceFromHigh(etf);
  const distanceSma200 = getDistanceFromSma200(etf);

  const phaseBase = {
    "Mid Trend": 15,
    "Early Trend": 11,
    Extended: 10,
    Weak: 3
  }[etf.trend] ?? 7;

  const trendQuality = clamp(
    phaseBase
      + (etf.price > etf.sma200 ? 5 : 0)
      + (etf.price > etf.sma50 ? 3 : 0)
      + (etf.sma50 > etf.sma200 ? 2 : 0),
    0,
    25
  );

  const momentum =
    scale(etf.perfMonth, -5, 10) * 5
    + scale(etf.perf3m, -10, 25) * 6
    + scale(etf.perf6m, -15, 40) * 5
    + scale(etf.perf1y, -20, 60) * 4;

  let highEntry = 0;
  if (distanceHigh <= -35) highEntry = 4;
  else if (distanceHigh <= -20) highEntry = 8;
  else if (distanceHigh <= -5) highEntry = 10;
  else if (distanceHigh <= 0) highEntry = 7;
  else highEntry = 3;

  let smaEntry = 0;
  if (distanceSma200 >= -5 && distanceSma200 <= 12) smaEntry = 10;
  else if (distanceSma200 > 12 && distanceSma200 <= 25) smaEntry = 7;
  else if (distanceSma200 > 25 && distanceSma200 <= 40) smaEntry = 4;
  else if (distanceSma200 > 40) smaEntry = 1;
  else smaEntry = 5;

  const entrySituation = highEntry + smaEntry;

  let volatilityPoints = 1;
  if (etf.volatility <= 15) volatilityPoints = 8;
  else if (etf.volatility <= 22) volatilityPoints = 6;
  else if (etf.volatility <= 30) volatilityPoints = 4;
  else if (etf.volatility <= 38) volatilityPoints = 2;

  let drawdownPoints = 1;
  if (etf.maxDrawdown >= -25) drawdownPoints = 7;
  else if (etf.maxDrawdown >= -35) drawdownPoints = 5;
  else if (etf.maxDrawdown >= -50) drawdownPoints = 3;

  const risk = volatilityPoints + drawdownPoints;

  const m1 = etf.perfMonth;
  const m3 = etf.perf3m / 3;
  const m6 = etf.perf6m / 6;
  const m12 = etf.perf1y / 12;
  const acceleration = clamp(
    (m1 > m3 ? 4 : m1 > 0 ? 2 : 0)
      + (m3 > m6 ? 3 : m3 > 0 ? 1 : 0)
      + (m6 > m12 ? 2 : m6 > 0 ? 1 : 0)
      + (etf.perfMonth > 0 && etf.perf3m > 0 ? 1 : 0),
    0,
    10
  );

  let fiveYearPoints = 2;
  if (hasHistory(etf.perf5y)) {
    fiveYearPoints = etf.perf5y > 30 ? 4 : etf.perf5y > 0 ? 3 : 1;
  }

  let threeYearPoints = 1.5;
  if (hasHistory(etf.perf3y)) {
    threeYearPoints = etf.perf3y > 20 ? 3 : etf.perf3y > 0 ? 2 : 0;
  }

  const terPoints = etf.ter <= 0.25 ? 3 : etf.ter <= 0.45 ? 2 : etf.ter <= 0.65 ? 1 : 0;
  const stability = clamp(fiveYearPoints + threeYearPoints + terPoints, 0, 10);

  const components = [
    {
      key: "trend",
      label: "Trendqualität",
      score: round1(trendQuality),
      max: 25,
      explanation: `${etf.trend}, Kurs ${distanceSma200 >= 0 ? "über" : "unter"} SMA 200, ${etf.sma50 > etf.sma200 ? "SMA 50 über SMA 200" : "SMA 50 nicht über SMA 200"}.`
    },
    {
      key: "momentum",
      label: "Momentum",
      score: round1(momentum),
      max: 20,
      explanation: `Bewertet 1, 3, 6 und 12 Monate. Aktuell: ${formatPct(etf.perfMonth)}, ${formatPct(etf.perf3m)}, ${formatPct(etf.perf6m)}, ${formatPct(etf.perf1y)}.`
    },
    {
      key: "entry",
      label: "Einstiegssituation",
      score: round1(entrySituation),
      max: 20,
      explanation: `${formatPct(distanceHigh)} zum 52W Hoch und ${formatPct(distanceSma200)} zum SMA 200. Zu starke Überdehnung wird abgewertet.`
    },
    {
      key: "risk",
      label: "Risiko",
      score: round1(risk),
      max: 15,
      explanation: `Volatilität ${formatNumber(etf.volatility, 1)} %, maximaler Drawdown ${formatPct(etf.maxDrawdown)}. Niedrigere Schwankungen erhalten mehr Punkte.`
    },
    {
      key: "acceleration",
      label: "Trendbeschleunigung",
      score: round1(acceleration),
      max: 10,
      explanation: "Vergleicht das jüngste Momentum mit den längeren Zeiträumen. Beschleunigendes Momentum erhält mehr Punkte."
    },
    {
      key: "stability",
      label: "Langfristige Stabilität",
      score: round1(stability),
      max: 10,
      explanation: `Berücksichtigt 3J (${formatHistoryPct(etf.perf3y)}), 5J (${formatHistoryPct(etf.perf5y)}) und TER (${formatNumber(etf.ter)} %). Bei jungen ETFs wird fehlende Historie neutral behandelt.`
    }
  ];

  const total = Math.round(components.reduce((sum, component) => sum + component.score, 0));
  return { total: clamp(total, 0, 100), components };
}

ETF_DATA.forEach((etf) => {
  const result = calculateOpportunityScore(etf);
  etf.score = result.total;
  etf.scoreBreakdown = result.components;
});

function scoreBreakdownMarkup(etf) {
  const components = etf.scoreBreakdown || [];
  return `
    <details class="score-details">
      <summary>Warum ${etf.score}/100?</summary>
      <div class="score-breakdown">
        ${components.map((component) => `
          <div class="score-component">
            <div class="score-component-head">
              <strong>${component.label}</strong>
              <span>${formatNumber(component.score, 1)}/${component.max}</span>
            </div>
            <div class="score-bar" aria-hidden="true">
              <span style="width:${clamp((component.score / component.max) * 100, 0, 100)}%"></span>
            </div>
            <p>${component.explanation}</p>
          </div>`).join("")}
        <div class="score-total-row">
          <strong>Gesamt</strong>
          <strong>${etf.score}/100</strong>
        </div>
        <p class="score-note">Der Score ist eine quantitative Orientierung, kein Kaufsignal. Die Gewichtung ist aktuell: Trend 25, Momentum 20, Einstieg 20, Risiko 15, Beschleunigung 10, langfristige Stabilität 10 Punkte.</p>
      </div>
    </details>`;
}

function switchView(viewId) {
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active-view", view.id === viewId);
  });

  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewId);
  });

  const titleMap = {
    dashboard: "Dashboard",
    favorites: "Meine ETFs",
    radar: "ETF Radar",
    watchlist: "Watchlist",
    compare: "Vergleich"
  };

  document.getElementById("pageTitle").textContent = titleMap[viewId] || "ETF Tracker";
}

function renderDashboard() {
  document.getElementById("favoriteCount").textContent = state.favorites.length;
  document.getElementById("watchlistCount").textContent = state.watchlist.length;

  const top = [...ETF_DATA].sort((a, b) => b.score - a.score)[0];
  document.getElementById("topOpportunityName").textContent = top ? top.symbol : "–";
  document.getElementById("topOpportunityScore").textContent = top ? `${top.score}/100 · ${top.trend}` : "Keine Daten";

  const favoriteContainer = document.getElementById("dashboardFavorites");
  const favoriteEtfs = state.favorites.map(getEtf).filter(Boolean).slice(0, 5);
  favoriteContainer.innerHTML = favoriteEtfs.length
    ? favoriteEtfs.map(compactRow).join("")
    : emptyState("Noch keine Favoriten ausgewählt.");

  const radarContainer = document.getElementById("dashboardRadar");
  const radarEtfs = [...ETF_DATA].sort((a, b) => b.score - a.score).slice(0, 5);
  radarContainer.innerHTML = radarEtfs.map(compactRadarRow).join("");
}

function compactRow(etf) {
  return `
    <div class="compact-row">
      <div class="compact-name">
        <strong>${etf.symbol}</strong>
        <span>${etf.name}</span>
      </div>
      <div class="metric ${performanceClass(etf.perfDay)}">${formatPct(etf.perfDay)}</div>
      <div class="metric ${performanceClass(etf.perfWeek)}">${formatPct(etf.perfWeek)}</div>
      <div class="metric ${performanceClass(etf.perf1y)}">${formatPct(etf.perf1y)}</div>
    </div>`;
}

function compactRadarRow(etf) {
  return `
    <div class="compact-row">
      <div class="compact-name">
        <strong>${etf.symbol}</strong>
        <span>${etf.trend}</span>
      </div>
      <div class="metric"><strong>${etf.score}</strong>/100</div>
      <div class="metric ${performanceClass(etf.perf3m)}">${formatPct(etf.perf3m)}</div>
      <div class="metric ${performanceClass(getDistanceFromHigh(etf))}">${formatPct(getDistanceFromHigh(etf))}</div>
    </div>`;
}

function renderFavorites() {
  const query = (document.getElementById("favoriteSearch")?.value || "").trim().toLowerCase();
  const etfs = state.favorites
    .map(getEtf)
    .filter(Boolean)
    .filter((etf) => !query || [etf.name, etf.symbol, etf.isin, etf.category].some((field) => field.toLowerCase().includes(query)));

  const container = document.getElementById("favoritesTable");
  if (!etfs.length) {
    container.innerHTML = emptyState("Keine passenden Favoriten gefunden. Füge ETFs über den ETF Radar hinzu.");
    return;
  }

  container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>ETF</th>
          <th>1h</th>
          <th>Heute</th>
          <th>1 Woche</th>
          <th>1 Monat</th>
          <th>3 Monate</th>
          <th>YTD</th>
          <th>1 Jahr</th>
          <th>3 Jahre</th>
          <th>5 Jahre</th>
          <th>TER</th>
          <th>52W Hoch</th>
          <th>Score</th>
        </tr>
      </thead>
      <tbody>
        ${etfs.map((etf) => `
          <tr>
            <td>
              <strong>${etf.symbol}</strong><br>
              <span class="muted">${etf.name}</span>
            </td>
            ${performanceCell(etf.perf1h)}
            ${performanceCell(etf.perfDay)}
            ${performanceCell(etf.perfWeek)}
            ${performanceCell(etf.perfMonth)}
            ${performanceCell(etf.perf3m)}
            ${performanceCell(etf.perfYtd)}
            ${performanceCell(etf.perf1y)}
            ${historyPerformanceCell(etf.perf3y)}
            ${historyPerformanceCell(etf.perf5y)}
            <td>${formatNumber(etf.ter)} %</td>
            <td class="${performanceClass(getDistanceFromHigh(etf))}">${formatPct(getDistanceFromHigh(etf))}</td>
            <td><strong>${etf.score}</strong>/100</td>
          </tr>`).join("")}
      </tbody>
    </table>`;
}

function performanceCell(value) {
  return `<td class="${performanceClass(value)}">${formatPct(value)}</td>`;
}

function historyPerformanceCell(value) {
  return `<td class="${hasHistory(value) ? performanceClass(value) : ""}">${formatHistoryPct(value)}</td>`;
}

function renderRadar() {
  const category = document.getElementById("categoryFilter")?.value || "all";
  const trend = document.getElementById("trendFilter")?.value || "all";

  const filtered = ETF_DATA
    .filter((etf) => category === "all" || etf.category === category)
    .filter((etf) => trend === "all" || etf.trend === trend)
    .sort((a, b) => b.score - a.score);

  const container = document.getElementById("radarGrid");
  container.innerHTML = filtered.length
    ? filtered.map(radarCard).join("")
    : emptyState("Für diese Filter gibt es aktuell keine ETFs.");
}

function radarCard(etf) {
  const isFavorite = state.favorites.includes(etf.id);
  const isWatchlist = state.watchlist.includes(etf.id);
  const distanceHigh = getDistanceFromHigh(etf);
  const distanceSma200 = getDistanceFromSma200(etf);

  return `
    <article class="radar-card">
      <div class="radar-card-top">
        <div>
          <span class="ticker">${etf.symbol} · ${etf.category}</span>
          <h3>${etf.name}</h3>
          <span class="trend-badge">${etf.trend}</span>
        </div>
        <div class="score-badge">${etf.score}</div>
      </div>

      <div class="card-metrics">
        <div class="card-metric">
          <span>3 Monate</span>
          <strong class="${performanceClass(etf.perf3m)}">${formatPct(etf.perf3m)}</strong>
        </div>
        <div class="card-metric">
          <span>1 Jahr</span>
          <strong class="${performanceClass(etf.perf1y)}">${formatPct(etf.perf1y)}</strong>
        </div>
        <div class="card-metric">
          <span>3 Jahre</span>
          <strong class="${hasHistory(etf.perf3y) ? performanceClass(etf.perf3y) : ""}">${formatHistoryPct(etf.perf3y)}</strong>
        </div>
        <div class="card-metric">
          <span>5 Jahre</span>
          <strong class="${hasHistory(etf.perf5y) ? performanceClass(etf.perf5y) : ""}">${formatHistoryPct(etf.perf5y)}</strong>
        </div>
        <div class="card-metric">
          <span>Abstand 52W Hoch</span>
          <strong class="${performanceClass(distanceHigh)}">${formatPct(distanceHigh)}</strong>
        </div>
        <div class="card-metric">
          <span>vs. SMA 200</span>
          <strong class="${performanceClass(distanceSma200)}">${formatPct(distanceSma200)}</strong>
        </div>
        <div class="card-metric">
          <span>Volatilität</span>
          <strong>${formatNumber(etf.volatility, 1)} %</strong>
        </div>
        <div class="card-metric">
          <span>TER</span>
          <strong>${formatNumber(etf.ter)} %</strong>
        </div>
      </div>

      <p class="muted">${etf.reason}</p>
      ${scoreBreakdownMarkup(etf)}

      <div class="card-actions">
        <button type="button" class="${isFavorite ? "active" : ""}" data-action="favorite" data-id="${etf.id}">${isFavorite ? "✓ Meine ETFs" : "+ Meine ETFs"}</button>
        <button type="button" class="${isWatchlist ? "active" : ""}" data-action="watchlist" data-id="${etf.id}">${isWatchlist ? "✓ Watchlist" : "+ Watchlist"}</button>
      </div>
    </article>`;
}

function renderWatchlist() {
  const etfs = state.watchlist.map(getEtf).filter(Boolean).sort((a, b) => b.score - a.score);
  const container = document.getElementById("watchlistGrid");
  container.innerHTML = etfs.length
    ? etfs.map(radarCard).join("")
    : emptyState("Deine Watchlist ist leer. Füge ETFs im ETF Radar hinzu.");
}

function populateCategoryFilter() {
  const select = document.getElementById("categoryFilter");
  if (!select) return;

  const categories = [...new Set(ETF_DATA.map((etf) => etf.category))].sort((a, b) => a.localeCompare(b, "de"));
  select.innerHTML = `<option value="all">Alle Kategorien</option>${categories.map((category) => `<option value="${category}">${category}</option>`).join("")}`;
}

function renderCompare() {
  const select = document.getElementById("compareSelect");
  select.innerHTML = ETF_DATA
    .filter((etf) => !state.compare.includes(etf.id))
    .sort((a, b) => a.name.localeCompare(b.name, "de"))
    .map((etf) => `<option value="${etf.id}">${etf.symbol} · ${etf.name}</option>`)
    .join("");

  const selection = document.getElementById("compareSelection");
  selection.innerHTML = state.compare
    .map(getEtf)
    .filter(Boolean)
    .map((etf) => `<span class="chip">${etf.symbol}<button type="button" data-remove-compare="${etf.id}" aria-label="${etf.symbol} entfernen">×</button></span>`)
    .join("");

  const etfs = state.compare.map(getEtf).filter(Boolean);
  const table = document.getElementById("compareTable");

  if (!etfs.length) {
    table.innerHTML = emptyState("Noch keine ETFs für den Vergleich ausgewählt.");
    return;
  }

  const rows = [
    ["Kategorie", (e) => e.category],
    ["Opportunity Score", (e) => `${e.score}/100`],
    ["Trendphase", (e) => e.trend],
    ["TER", (e) => `${formatNumber(e.ter)} %`],
    ["Heute", (e) => formatPct(e.perfDay)],
    ["1 Woche", (e) => formatPct(e.perfWeek)],
    ["3 Monate", (e) => formatPct(e.perf3m)],
    ["1 Jahr", (e) => formatPct(e.perf1y)],
    ["3 Jahre", (e) => formatHistoryPct(e.perf3y)],
    ["5 Jahre", (e) => formatHistoryPct(e.perf5y)],
    ["Trendqualität", (e) => `${formatNumber(e.scoreBreakdown.find((c) => c.key === "trend")?.score || 0, 1)}/25`],
    ["Momentum", (e) => `${formatNumber(e.scoreBreakdown.find((c) => c.key === "momentum")?.score || 0, 1)}/20`],
    ["Einstiegssituation", (e) => `${formatNumber(e.scoreBreakdown.find((c) => c.key === "entry")?.score || 0, 1)}/20`],
    ["Risiko Score", (e) => `${formatNumber(e.scoreBreakdown.find((c) => c.key === "risk")?.score || 0, 1)}/15`],
    ["Trendbeschleunigung", (e) => `${formatNumber(e.scoreBreakdown.find((c) => c.key === "acceleration")?.score || 0, 1)}/10`],
    ["Langfristige Stabilität", (e) => `${formatNumber(e.scoreBreakdown.find((c) => c.key === "stability")?.score || 0, 1)}/10`],
    ["Volatilität", (e) => `${formatNumber(e.volatility, 1)} %`],
    ["Max. Drawdown", (e) => formatPct(e.maxDrawdown)],
    ["Abstand 52W Hoch", (e) => formatPct(getDistanceFromHigh(e))],
    ["Abstand SMA 200", (e) => formatPct(getDistanceFromSma200(e))]
  ];

  table.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Kennzahl</th>
          ${etfs.map((etf) => `<th>${etf.symbol}</th>`).join("")}
        </tr>
      </thead>
      <tbody>
        ${rows.map(([label, getter]) => `
          <tr>
            <td><strong>${label}</strong></td>
            ${etfs.map((etf) => `<td>${getter(etf)}</td>`).join("")}
          </tr>`).join("")}
      </tbody>
    </table>`;
}

function emptyState(message) {
  return `<div class="empty-state">${message}</div>`;
}

function toggleInArray(arrayName, id) {
  const array = state[arrayName];
  const index = array.indexOf(id);
  if (index >= 0) array.splice(index, 1);
  else array.push(id);
  saveState();
  renderAll();
}

function resetSelections() {
  state.favorites = [...DEFAULTS.favorites];
  state.watchlist = [...DEFAULTS.watchlist];
  state.compare = [];
  saveState();
  renderAll();
}

function renderAll() {
  renderDashboard();
  renderFavorites();
  renderRadar();
  renderWatchlist();
  renderCompare();
}

function bindEvents() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });

  document.querySelectorAll("[data-jump]").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.jump));
  });

  document.getElementById("favoriteSearch")?.addEventListener("input", renderFavorites);
  document.getElementById("categoryFilter")?.addEventListener("change", renderRadar);
  document.getElementById("trendFilter")?.addEventListener("change", renderRadar);

  document.body.addEventListener("click", (event) => {
    const actionButton = event.target.closest("[data-action]");
    if (actionButton) {
      toggleInArray(actionButton.dataset.action === "favorite" ? "favorites" : "watchlist", actionButton.dataset.id);
      return;
    }

    const removeButton = event.target.closest("[data-remove-compare]");
    if (removeButton) {
      state.compare = state.compare.filter((id) => id !== removeButton.dataset.removeCompare);
      saveState();
      renderCompare();
    }
  });

  document.getElementById("addCompare")?.addEventListener("click", () => {
    const select = document.getElementById("compareSelect");
    const id = select.value;
    if (!id || state.compare.includes(id)) return;
    if (state.compare.length >= 4) {
      alert("Du kannst maximal vier ETFs gleichzeitig vergleichen.");
      return;
    }
    state.compare.push(id);
    saveState();
    renderCompare();
  });

  document.getElementById("clearCompare")?.addEventListener("click", () => {
    state.compare = [];
    saveState();
    renderCompare();
  });

  document.getElementById("resetData")?.addEventListener("click", resetSelections);
}

populateCategoryFilter();
bindEvents();
renderAll();
