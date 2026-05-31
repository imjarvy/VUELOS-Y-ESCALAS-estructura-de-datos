// Builds and updates report DOM. No fetch, no state writes.
import { formatMoney, formatMinutes } from "../../utils/formatters.js";
import { state } from "./report-state.js";

const DECISION_LABELS = {
  transport: "Vuelo",
  activity: "Actividad",
  job: "Trabajo",
  skip: "Omitir",
  interruption: "Interrupción",
};

function pick(obj, ...keys) {
  for (const key of keys) {
    if (obj?.[key] != null && obj[key] !== "") return obj[key];
  }
  return null;
}

function setListContent(listEl, items, renderItem, emptyText) {
  listEl.innerHTML = "";
  if (!items?.length) {
    const li = document.createElement("li");
    li.className = "report-empty-item";
    li.textContent = emptyText;
    listEl.appendChild(li);
    return;
  }
  items.forEach(item => listEl.appendChild(renderItem(item)));
}

function formatDecisionDetails(decision) {
  const details = decision.details || {};
  const kind = String(decision.kind || "").toLowerCase();

  if (kind === "transport") {
    const origin = pick(details, "origin", "origin_id");
    const dest = pick(details, "destination", "destination_id");
    const cost = pick(details, "cost_usd", "costUSD", "leg_cost");
    const time = pick(details, "time_min", "flight_time_min", "flightTimeMin");
    const subsidized = details.is_subsidized ? " · subsidiado" : "";
    return `${origin} → ${dest} · ${details.aircraft || "-"} · ${formatMoney(cost)} · ${formatMinutes(time)}${subsidized}`;
  }

  if (kind === "activity") {
    const name = pick(details, "name", "nombre", "activity_name");
    const cost = pick(details, "cost_usd", "costoUSD", "cost");
    const duration = pick(details, "duration_min", "duracionMin");
    return `${name || "-"} · ${formatMinutes(duration)} · ${formatMoney(cost)}`;
  }

  if (kind === "job") {
    const name = pick(details, "name", "nombre", "job_name");
    const hours = pick(details, "hours_worked", "hoursWorked", "hours");
    const income = pick(details, "income_usd", "earnedUSD", "income");
    return `${name || "-"} · ${hours ?? 0} h · ${formatMoney(income)}`;
  }

  if (kind === "skip") {
    return pick(details, "reason", "motivo") || "Decisión omitida";
  }

  if (kind === "interruption") {
    const pct = details.porcentaje_recorrido != null
      ? `${Math.round(Number(details.porcentaje_recorrido) * 100)}%`
      : "-";
    return `Tramo ${details.tramo_afectado || "-"} · regreso a ${details.regreso_a || "-"} · ${pct} recorrido`;
  }

  try {
    return JSON.stringify(details);
  } catch {
    return String(details);
  }
}

export function showBanner(banner, text, kind = "info") {
  banner.textContent = text;
  banner.dataset.kind = kind;
  banner.style.display = text ? "" : "none";
}

export function updateLoadButton(loadBtn) {
  loadBtn.disabled = state.loading || !state.sessionId;
  loadBtn.textContent = state.loading ? "Cargando…" : "Cargar reporte";
}

function renderVisited(listEl, visited) {
  setListContent(
    listEl,
    visited,
    entry => {
      const li = document.createElement("li");
      const code = pick(entry, "airport_id", "id") || "-";
      const name = pick(entry, "name", "nombre") || code;
      const city = pick(entry, "city", "ciudad") || "";
      const country = pick(entry, "country", "pais") || "";
      const timezone = pick(entry, "timezone", "zonaHoraria");
      const place = [city, country].filter(Boolean).join(", ");
      const tz = timezone ? ` · ${timezone}` : "";
      li.textContent = place
        ? `${code} · ${name} (${place})${tz}`
        : `${code} · ${name}${tz}`;
      return li;
    },
    "Todavía no hay destinos en el reporte.",
  );
}

function renderLegs(listEl, legs) {
  let accCost = 0;
  let accTime = 0;

  setListContent(
    listEl,
    legs,
    leg => {
      const li = document.createElement("li");
      const origin = pick(leg, "origin_id", "origin") || "-";
      const dest = pick(leg, "destination_id", "destination", "dest") || "-";
      const aircraft = leg.aircraft || "-";
      const dist = Number(pick(leg, "distance", "distanceKm", "distance_km") ?? 0);
      const cost = Number(pick(leg, "leg_cost", "costUSD", "cost_usd") ?? 0);
      const time = Number(pick(leg, "flight_time_min", "flightTimeMin", "time_min") ?? 0);
      accCost += cost;
      accTime += time;
      li.textContent =
        `${origin} → ${dest} · ${aircraft} · ${dist.toFixed(0)} km · ${formatMoney(cost)} · ${formatMinutes(time)} · acum. ${formatMoney(accCost)} / ${formatMinutes(accTime)}`;
      return li;
    },
    "No hay tramos registrados.",
  );
}

function renderActivities(listEl, activities) {
  setListContent(
    listEl,
    activities,
    act => {
      const li = document.createElement("li");
      const name = pick(act, "name", "nombre") || "-";
      const type = pick(act, "type", "tipo", "activity_type", "kind") || "";
      const duration = pick(act, "duration_min", "duracionMin");
      const cost = pick(act, "cost_usd", "costoUSD", "cost");
      const performedAt = pick(act, "performed_at_min", "performedAtMin");
      const atLabel = performedAt != null ? ` · min ${performedAt} del viaje` : "";
      li.textContent =
        `${name} · ${type} · ${formatMinutes(duration)} · ${formatMoney(cost)}${atLabel}`;
      return li;
    },
    "No se registraron actividades.",
  );
}

function renderJobs(listEl, jobs) {
  setListContent(
    listEl,
    jobs,
    job => {
      const li = document.createElement("li");
      const name = pick(job, "name", "nombre") || "-";
      const rate = pick(job, "hourly_rate", "hourlyRate", "tarifaHora");
      const hours = pick(job, "hours_worked", "hoursWorked", "hours") ?? 0;
      const income = pick(job, "income_usd", "earnedUSD", "income");
      li.textContent =
        `${name} · ${formatMoney(rate)}/h · ${hours} h trabajadas · ${formatMoney(income)} ganados`;
      return li;
    },
    "No se registraron trabajos.",
  );
}

function renderDecisions(listEl, decisions) {
  setListContent(
    listEl,
    decisions,
    decision => {
      const li = document.createElement("li");
      const kind = String(decision.kind || "").toLowerCase();
      const label = DECISION_LABELS[kind] || decision.kind || "Decisión";
      const when = decision.timestamp_min != null
        ? formatMinutes(decision.timestamp_min)
        : "-";
      li.textContent = `[${label}] · ${when} · ${formatDecisionDetails(decision)}`;
      return li;
    },
    "No hay decisiones registradas en la sesión.",
  );
}

function renderTotals(blockEl, totals, destinationCount) {
  blockEl.innerHTML = "";
  if (!totals || !Object.keys(totals).length) {
    blockEl.textContent = "Sin totales disponibles.";
    return;
  }

  const rows = [
    ["Presupuesto inicial", formatMoney(pick(totals, "budget_initial", "budgetInitialUSD"))],
    ["Total gastado", formatMoney(pick(totals, "total_spent", "totalSpentUSD"))],
    ["Total ganado", formatMoney(pick(totals, "total_gained", "totalEarnedUSD"))],
    ["Saldo final", formatMoney(pick(totals, "final_balance", "balanceUSD"))],
    ["Tiempo total", formatMinutes(pick(totals, "time_total_min", "totalTravelTimeMin"))],
    ["Destinos visitados", destinationCount != null ? String(destinationCount) : "-"],
    ["Distancia recorrida", (() => {
      const km = pick(totals, "distance_travelled_km", "distanceTravelledKm");
      return km != null ? `${km} km` : "-";
    })()],
    ["Distancia subsidiada", (() => {
      const km = pick(totals, "subsidized_distance_km", "subsidizedDistanceKm");
      return km != null ? `${km} km` : "-";
    })()],
  ];

  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "info-row report-total-row";
    row.innerHTML = `<span class="info-label">${label}</span><strong>${value}</strong>`;
    blockEl.appendChild(row);
  });
}

export function renderReport(refs, data) {
  if (!data) return;

  const visited = data.visited || data.visitedAirports || [];

  refs.sessionIdEl.textContent = data.session_id || data.sessionId || state.sessionId || "-";
  renderVisited(refs.visitedList, visited);
  renderLegs(refs.legsList, data.legs || []);
  renderActivities(refs.activitiesList, data.activities || []);
  renderJobs(refs.jobsList, data.jobs || []);
  renderDecisions(refs.decisionsList, data.decisions || []);
  renderTotals(refs.totalsBlock, data.totals || {}, visited.length);
}

export function renderEmptyReport(refs) {
  refs.sessionIdEl.textContent = "-";
  renderVisited(refs.visitedList, []);
  renderLegs(refs.legsList, []);
  renderActivities(refs.activitiesList, []);
  renderJobs(refs.jobsList, []);
  renderDecisions(refs.decisionsList, []);
  renderTotals(refs.totalsBlock, {}, 0);
}
