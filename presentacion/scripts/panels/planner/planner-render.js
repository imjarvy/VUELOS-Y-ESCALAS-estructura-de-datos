// Builds and updates planner DOM. No fetch, no state writes.
import { formatMoney, formatMinutes } from "../../utils/formatters.js";
import { state } from "./planner-state.js";

export function showBanner(banner, text, kind = "info") {
  banner.textContent = text;
  banner.dataset.kind = kind;
  banner.style.display = "";
}

export function render(panel, submitBtn) {
  panel.querySelectorAll(".planner-mode-btn").forEach(btn => {
    btn.classList.toggle("session-action-primary", btn.dataset.mode === state.mode);
  });

  panel.querySelectorAll(".planner-mode-section").forEach(sec => {
    sec.style.display = sec.dataset.section === state.mode ? "" : "none";
  });

  submitBtn.disabled = !state.graphLoaded || state.loading;
  submitBtn.textContent = state.loading ? "Calculando…" : "Calcular itinerario";
}

function buildItineraryCard(label, itin, onHighlight) {
  if (!itin) {
    const empty = document.createElement("div");
    empty.className = "session-empty";
    empty.textContent = "No se encontró ruta con las restricciones dadas.";
    return empty;
  }

  const card = document.createElement("div");
  card.className = "session-proposal-card";

  const header = document.createElement("div");
  header.className = "session-proposal-header";
  header.innerHTML = `
    <strong>${label}</strong>
    <span>Criterio: ${itin.optimization_criteria}</span>`;

  const tagRow = document.createElement("div");
  tagRow.className = "session-tag-row";
  [
    `${(itin.visited_airports || []).length} aeropuertos`,
    formatMoney(itin.total_cost),
    formatMinutes(itin.total_time_min),
  ].forEach(txt => {
    const tag = document.createElement("span");
    tag.className = "session-tag";
    tag.textContent = txt;
    tagRow.appendChild(tag);
  });

  const legsList = document.createElement("div");
  (itin.legs || []).forEach(leg => {
    const row = document.createElement("div");
    row.className = "session-choice-row";
    row.innerHTML = `
      <div class="session-choice-main">
        <strong>${leg.origin_id} → ${leg.destination_id}</strong>
        <span>${leg.aircraft} · ${Number(leg.distance).toFixed(0)} km · ${formatMoney(leg.leg_cost)} · ${formatMinutes(leg.flight_time_min)}</span>
      </div>`;
    legsList.appendChild(row);
  });

  const content = document.createElement("div");
  content.className = "session-proposal-content";
  content.appendChild(legsList);
  content.appendChild(tagRow);

  if (typeof onHighlight === "function" && itin.legs?.length) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-sm session-action-btn session-action-primary";
    btn.textContent = "Ver en el mapa";
    btn.addEventListener("click", () => onHighlight(itin));
    content.appendChild(btn);
  }

  card.appendChild(header);
  card.appendChild(content);
  return card;
}

export function renderResults(resultsList, resultsSection, onHighlight) {
  resultsList.innerHTML = "";
  resultsSection.style.display = "";

  if (state.mode === "basic") {
    resultsList.appendChild(
      buildItineraryCard("A — Máx. destinos por presupuesto", state.itinerary_a, onHighlight),
    );
    resultsList.appendChild(
      buildItineraryCard("B — Máx. destinos por tiempo", state.itinerary_b, onHighlight),
    );
    return;
  }

  const labels = { cost: "Menor costo", time: "Menor tiempo", distance: "Menor distancia" };
  Object.entries(state.routes || {}).forEach(([criterion, itin]) => {
    resultsList.appendChild(
      buildItineraryCard(labels[criterion] || criterion, itin, onHighlight),
    );
  });
}
