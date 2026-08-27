const ETF_HELP = {
  score: "Opportunity Score von 0 bis 100. Er kombiniert Trendqualität, Momentum, Einstiegssituation, Risiko, Trendbeschleunigung und langfristige Stabilität. Ein hoher Wert bedeutet: quantitativ interessant. Er ist kein Kaufsignal.",
  "Early Trend": "Early Trend: Der ETF zeigt erste Anzeichen eines neuen Aufwärtstrends. Das kann eine interessante frühe Phase sein, ist aber noch weniger bestätigt als ein etablierter Trend.",
  "Mid Trend": "Mid Trend: Der Aufwärtstrend ist bereits etabliert, wirkt aber noch nicht stark überdehnt. Das ist oft die ausgewogenste Trendphase.",
  Extended: "Extended: Der ETF ist bereits stark gelaufen und liegt oft deutlich über seinem längerfristigen Durchschnitt. Der Trend kann weitergehen, das Rückschlagrisiko ist aber erhöht.",
  Weak: "Weak: Der Trend ist aktuell schwach oder negativ. Das bedeutet nicht automatisch, dass der ETF schlecht ist, technisch fehlt aber momentan Stärke.",
  ter: "TER, Total Expense Ratio: laufende Fondskosten pro Jahr. 0,20 % bedeutet ungefähr CHF 2 Kosten pro CHF 1'000 Fondsvermögen und Jahr. Die Kosten werden im Fonds verrechnet.",
  high52: "Abstand zum 52-Wochen-Hoch: zeigt, wie weit der aktuelle Kurs unter dem höchsten Kurs der letzten 52 Wochen liegt. Zum Beispiel −15 % bedeutet 15 % unter dem Jahreshoch.",
  sma200: "SMA 200: gleitender Durchschnitt der letzten 200 Handelstage. Ein Kurs über dem SMA 200 spricht oft für einen intakten langfristigen Aufwärtstrend. Ein sehr grosser Abstand kann auf Überdehnung hindeuten.",
  volatility: "Volatilität: misst, wie stark der Kurs schwankt. Je höher der Wert, desto grösser sind typischerweise die kurzfristigen Ausschläge nach oben und unten.",
  drawdown: "Maximaler Drawdown: grösster historischer Rückgang vom damaligen Hoch bis zum folgenden Tief im betrachteten Zeitraum. Je negativer, desto heftiger war der grösste Einbruch.",
  ytd: "YTD, Year to Date: Performance seit dem ersten Handelstag des laufenden Jahres.",
  performance: "Performance in diesem Zeitraum. Positive Werte bedeuten Kursanstieg, negative Werte Kursrückgang. In der Demo-Version sind diese Werte noch Testdaten."
};

function addHelp(element, text) {
  if (!element || !text) return;
  element.classList.add("explainable");
  element.setAttribute("data-tooltip", text);
  if (!element.hasAttribute("tabindex")) element.setAttribute("tabindex", "0");
  element.setAttribute("aria-label", `${element.textContent.trim()}. ${text}`);
}

function annotateHelp() {
  document.querySelectorAll(".score-badge").forEach((el) => addHelp(el, ETF_HELP.score));

  const topScore = document.getElementById("topOpportunityScore");
  if (topScore) addHelp(topScore, ETF_HELP.score);

  document.querySelectorAll(".trend-badge").forEach((el) => {
    const key = el.textContent.trim();
    addHelp(el, ETF_HELP[key]);
  });

  document.querySelectorAll(".compact-name span").forEach((el) => {
    const key = el.textContent.trim();
    if (ETF_HELP[key]) addHelp(el, ETF_HELP[key]);
  });

  document.querySelectorAll("th, .card-metric span, td:first-child strong").forEach((el) => {
    const label = el.textContent.trim().toLowerCase();

    if (label === "score" || label.includes("opportunity score")) addHelp(el, ETF_HELP.score);
    else if (label === "ter") addHelp(el, ETF_HELP.ter);
    else if (label.includes("52w hoch") || label.includes("52-wochen-hoch")) addHelp(el, ETF_HELP.high52);
    else if (label.includes("sma 200")) addHelp(el, ETF_HELP.sma200);
    else if (label.includes("volatilität")) addHelp(el, ETF_HELP.volatility);
    else if (label.includes("drawdown")) addHelp(el, ETF_HELP.drawdown);
    else if (label === "ytd") addHelp(el, ETF_HELP.ytd);
    else if (["1h", "heute", "1 woche", "1 monat", "3 monate", "1 jahr", "3 jahre", "5 jahre"].includes(label)) addHelp(el, ETF_HELP.performance);
    else if (label === "trendphase") addHelp(el, "Trendphase: unsere technische Einordnung des aktuellen Kursverlaufs. Fahre über die konkrete Trendbezeichnung, um ihre Bedeutung zu sehen.");
  });
}

let helpScheduled = false;
function scheduleHelp() {
  if (helpScheduled) return;
  helpScheduled = true;
  requestAnimationFrame(() => {
    helpScheduled = false;
    annotateHelp();
  });
}

window.addEventListener("DOMContentLoaded", scheduleHelp);

const helpObserver = new MutationObserver(scheduleHelp);
helpObserver.observe(document.body, { childList: true, subtree: true });
