// Coordinates report panel: DOM shell, events, API calls and render updates.
import { fetchSessionReport } from "./report-api.js";
import { state } from "./report-state.js";
import { renderReport, renderEmptyReport, showBanner, updateLoadButton } from "./report-render.js";

export function createReportPanel({ panelId = "reportPanel" } = {}) {
  const panel = document.getElementById(panelId);
  if (!panel) {
    throw new Error(`Report panel #${panelId} was not found.`);
  }

  panel.innerHTML = `
    <h3>Reporte del viaje</h3>

    <div class="info-row">
      <span class="info-label">Sesión</span>
      <strong id="reportSessionId">-</strong>
    </div>

    <button id="reportLoadBtn" type="button"
            class="btn btn-sm session-action-btn session-action-primary"
            style="width:100%;margin-bottom:8px" disabled>
      Cargar reporte
    </button>

    <div class="session-banner" id="reportBanner" style="display:none"></div>

    <div class="info-block report-section">
      <span class="info-label">Destinos visitados</span>
      <ul id="reportVisitedList" class="info-list report-list"></ul>
    </div>

    <div class="info-block report-section">
      <span class="info-label">Tramos de vuelo</span>
      <ul id="reportLegsList" class="info-list report-list"></ul>
    </div>

    <div class="info-block report-section">
      <span class="info-label">Actividades</span>
      <ul id="reportActivitiesList" class="info-list report-list"></ul>
    </div>

    <div class="info-block report-section">
      <span class="info-label">Trabajos</span>
      <ul id="reportJobsList" class="info-list report-list"></ul>
    </div>

    <div class="info-block report-section">
      <span class="info-label">Decisiones</span>
      <ul id="reportDecisionsList" class="info-list report-list"></ul>
    </div>

    <div class="info-block report-section">
      <span class="info-label">Totales</span>
      <div id="reportTotalsBlock" class="report-totals"></div>
    </div>`;

  const refs = {
    loadBtn: panel.querySelector("#reportLoadBtn"),
    banner: panel.querySelector("#reportBanner"),
    sessionIdEl: panel.querySelector("#reportSessionId"),
    visitedList: panel.querySelector("#reportVisitedList"),
    legsList: panel.querySelector("#reportLegsList"),
    activitiesList: panel.querySelector("#reportActivitiesList"),
    jobsList: panel.querySelector("#reportJobsList"),
    decisionsList: panel.querySelector("#reportDecisionsList"),
    totalsBlock: panel.querySelector("#reportTotalsBlock"),
  };

  let _onHighlightRoute = null;
  function onHighlightRoute(handler) { _onHighlightRoute = handler; }

  function clear() {
    state.sessionId = null;
    state.loading = false;
    renderEmptyReport(refs);
    showBanner(refs.banner, "");
    updateLoadButton(refs.loadBtn);
    if (typeof _onHighlightRoute === "function") _onHighlightRoute(null);
  }

  function setSessionId(sessionId) {
    state.sessionId = sessionId ? String(sessionId) : null;
    refs.sessionIdEl.textContent = state.sessionId || "-";
    updateLoadButton(refs.loadBtn);
  }

  async function loadReport(sessionId, { quiet = false } = {}) {
    const id = sessionId || state.sessionId;
    if (!id) {
      showBanner(refs.banner, "No hay sesión activa para cargar el reporte.", "error");
      return null;
    }

    state.loading = true;
    if (!quiet) showBanner(refs.banner, "");
    updateLoadButton(refs.loadBtn);

    try {
      const data = await fetchSessionReport(id);
      state.sessionId = id;
      refs.sessionIdEl.textContent = id;
      renderReport(refs, data);
      if (typeof _onHighlightRoute === "function") _onHighlightRoute(data);
      if (!quiet) {
        showBanner(refs.banner, "Reporte cargado correctamente.", "success");
      }
      return data;
    } catch (err) {
      showBanner(refs.banner, err.message || "No se pudo cargar el reporte.", "error");
      return null;
    } finally {
      state.loading = false;
      updateLoadButton(refs.loadBtn);
    }
  }

  function setAvailability({ sessionActive } = {}) {
    if (sessionActive === false && !state.sessionId) {
      refs.loadBtn.disabled = true;
    } else {
      updateLoadButton(refs.loadBtn);
    }
  }

  refs.loadBtn.addEventListener("click", () => {
    loadReport(state.sessionId);
  });

  clear();

  return {
    setSessionId,
    loadReport,
    renderReport: data => {
      renderReport(refs, data);
      if (typeof _onHighlightRoute === "function") _onHighlightRoute(data);
    },
    clear,
    setAvailability,
    onHighlightRoute,
    show: () => panel.classList.remove("hidden"),
    hide: () => panel.classList.add("hidden"),
  };
}
