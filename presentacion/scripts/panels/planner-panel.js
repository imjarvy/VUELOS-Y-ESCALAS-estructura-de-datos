// Coordina estado, render y llamadas a la API.
// No construye DOM complejo ni formatea datos — eso está en planner-render.js.
import { apiPost } from "../api/client.js";
import { state }   from "./planner-state.js";
import { render, renderResults, showBanner } from "./planner-render.js";

export function createPlannerPanel({ panelId = "plannerPanel" } = {}) {
  const panel = document.getElementById(panelId);
  if (!panel) throw new Error(`Panel #${panelId} no encontrado.`);

  // ── Construir HTML del panel ─────────────────────────────────────────────
  panel.innerHTML = `
    <div class="info-row">
      <span class="info-label">Modo</span>
      <div class="planner-mode-toggle">
        <button class="btn btn-sm planner-mode-btn" data-mode="basic">Máx. destinos</button>
        <button class="btn btn-sm planner-mode-btn" data-mode="route">Mejor ruta</button>
      </div>
    </div>

    <div class="info-row">
      <label class="info-label" for="plannerOrigin">Origen</label>
      <input id="plannerOrigin" type="text" placeholder="BOG" maxlength="3"
             style="text-transform:uppercase;width:80px" />
    </div>

    <div class="planner-mode-section" data-section="basic">
      <div class="info-row">
        <label class="info-label" for="plannerBudget">Presupuesto (USD)</label>
        <input id="plannerBudget" type="number" min="0" step="0.01" placeholder="600" style="width:100px" />
      </div>
      <div class="info-row">
        <label class="info-label" for="plannerTimeH">Tiempo disponible (h)</label>
        <input id="plannerTimeH" type="number" min="0" step="0.5"  placeholder="50"  style="width:80px" />
      </div>
    </div>

    <div class="planner-mode-section" data-section="route">
      <div class="info-row">
        <label class="info-label" for="plannerDest">Destino</label>
        <input id="plannerDest" type="text" placeholder="LIM" maxlength="3"
               style="text-transform:uppercase;width:80px" />
      </div>
      <div class="info-block">
        <span class="info-label">Criterios</span>
        <div class="planner-checkbox-group">
          <label><input type="checkbox" name="criteria" value="cost"     checked /> Costo</label>
          <label><input type="checkbox" name="criteria" value="time"            /> Tiempo</label>
          <label><input type="checkbox" name="criteria" value="distance"        /> Distancia</label>
        </div>
      </div>
    </div>

    <div class="info-block">
      <span class="info-label">Tipos de aeronave</span>
      <div class="planner-checkbox-group">
        <label><input type="checkbox" name="transport" value="Comercial" checked /> Comercial</label>
        <label><input type="checkbox" name="transport" value="Regional"  checked /> Regional</label>
        <label><input type="checkbox" name="transport" value="Hélice"    checked /> Hélice</label>
      </div>
      <div class="info-row" style="margin-top:8px">
        <span class="info-label">Aeropuertos secundarios</span>
        <label>
          <input type="checkbox" id="plannerSecondary" checked /> Incluir
        </label>
      </div>
    </div>

    <button id="plannerSubmitBtn" type="button"
            class="btn btn-sm session-action-btn session-action-primary"
            style="width:100%;margin-top:8px">
      Calcular itinerario
    </button>

    <div class="session-banner" id="plannerBanner" style="display:none"></div>

    <div id="plannerResultsSection" class="info-block" style="display:none">
      <span class="info-label">Resultados</span>
      <div id="plannerResultsList" class="session-proposals-list"></div>
    </div>`;

  // ── Referencias al DOM ───────────────────────────────────────────────────
  const submitBtn      = panel.querySelector("#plannerSubmitBtn");
  const banner         = panel.querySelector("#plannerBanner");
  const resultsList    = panel.querySelector("#plannerResultsList");
  const resultsSection = panel.querySelector("#plannerResultsSection");

  let _onHighlightRoute = null;
  function onHighlightRoute(handler) { _onHighlightRoute = handler; }

  // ── Leer inputs ──────────────────────────────────────────────────────────
  function getOrigin() {
    return (panel.querySelector("#plannerOrigin")?.value || "").trim().toUpperCase();
  }
  function getTransportTypes() {
    return [...panel.querySelectorAll("input[name='transport']:checked")]
      .map(cb => cb.value);
  }
  function getCriteria() {
    return [...panel.querySelectorAll("input[name='criteria']:checked")]
      .map(cb => cb.value);
  }
  function includeSecondary() {
    return panel.querySelector("#plannerSecondary")?.checked ?? true;
  }

  // ── Llamadas a la API ────────────────────────────────────────────────────
  async function submitBasic() {
    const origin    = getOrigin();
    const budget    = parseFloat(panel.querySelector("#plannerBudget")?.value);
    const timeHours = parseFloat(panel.querySelector("#plannerTimeH")?.value);

    if (!origin)              return showBanner(banner, "Ingresa el aeropuerto de origen.", "error");
    if (!budget || budget<=0) return showBanner(banner, "Ingresa un presupuesto válido.", "error");
    if (!timeHours||timeHours<=0) return showBanner(banner, "Ingresa el tiempo disponible.", "error");

    state.loading = true;
    render(panel, submitBtn);
    banner.style.display = "none";

    try {
      const data = await apiPost("/api/plan/basic", {
        origin,
        budget,
        time_hours:        timeHours,
        transport_types:   getTransportTypes(),
        include_secondary: includeSecondary(),
      });
      state.itinerary_a = data.itinerary_a;
      state.itinerary_b = data.itinerary_b;
      renderResults(resultsList, resultsSection, _onHighlightRoute);
    } catch (err) {
      showBanner(banner, err.message || "Error al calcular.", "error");
    } finally {
      state.loading = false;
      render(panel, submitBtn);
    }
  }

  async function submitRoute() {
    const origin   = getOrigin();
    const dest     = (panel.querySelector("#plannerDest")?.value || "").trim().toUpperCase();
    const criteria = getCriteria();

    if (!origin || !dest) return showBanner(banner, "Ingresa origen y destino.", "error");
    if (!criteria.length)  return showBanner(banner, "Selecciona al menos un criterio.", "error");

    state.loading = true;
    render(panel, submitBtn);
    banner.style.display = "none";

    try {
      const data = await apiPost("/api/plan/route", {
        origin, dest, criteria,
        transport_types:   getTransportTypes(),
        include_secondary: includeSecondary(),
      });
      state.routes = data.routes;
      renderResults(resultsList, resultsSection, _onHighlightRoute);
    } catch (err) {
      showBanner(banner, err.message || "Error al calcular.", "error");
    } finally {
      state.loading = false;
      render(panel, submitBtn);
    }
  }

  // ── Eventos ──────────────────────────────────────────────────────────────
  panel.querySelectorAll(".planner-mode-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      state.mode = btn.dataset.mode;
      state.itinerary_a = state.itinerary_b = state.routes = null;
      resultsSection.style.display = "none";
      banner.style.display = "none";
      render(panel, submitBtn);
    });
  });

  submitBtn.addEventListener("click", () => {
    if (state.mode === "basic") submitBasic();
    else submitRoute();
  });

  // Forzar mayúsculas en los inputs de aeropuerto
  ["plannerOrigin", "plannerDest"].forEach(id => {
    panel.querySelector(`#${id}`)?.addEventListener("input", e => {
      const pos = e.target.selectionStart;
      e.target.value = e.target.value.toUpperCase();
      e.target.setSelectionRange(pos, pos);
    });
  });

  // ── API pública ──────────────────────────────────────────────────────────
  function setAvailability({ graphLoaded } = {}) {
    if (graphLoaded !== undefined) state.graphLoaded = Boolean(graphLoaded);
    render(panel, submitBtn);
  }

  render(panel, submitBtn);

  return { setAvailability, onHighlightRoute };
}