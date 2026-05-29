import { apiGet, apiPost, apiPostFormData } from "./api/client.js";
import { createGraphUi, transformGraphToD3Data } from "./graphUI.js";
import { FlightAnimator } from "./flightAnimator.js";
import { createInfoPanel } from "./panels/infoPanel.js";
import { createTripSessionPanel } from "./panels/tripSessionPanel.js";
import { createGraphConfigController } from "./graphConfigController.js";

const status = document.getElementById("status");
const jsonModal = document.getElementById("jsonModal");
const jsonFileInput = document.getElementById("jsonFile");
const fileLabel = document.getElementById("fileLabel");
const infoPanel = createInfoPanel({ panelId: "airportInfoPanel" });
const tripSessionPanel = createTripSessionPanel({ panelId: "tripSessionPanel" });

function openModal() {
  jsonModal.classList.remove("hidden");
}

function closeModal() {
  jsonModal.classList.add("hidden");
}

const graphUi = createGraphUi({
  state: { selectedCode: null },
  onNodeSelect: node => {
    infoPanel.show(node);
  },
});

const flightAnimator = new FlightAnimator({ svgId: "graphSvg" });

function getFirstRenderedLinkEndpoints() {
  const svg = document.getElementById("graphSvg");
  if (!svg) return null;

  const firstLink = svg.querySelector(".graph-links .link");
  const data = firstLink?.__data__;
  if (!data) return null;

  const origin = String(data._originId ?? data.origin_vertex ?? data.origin ?? data.source?.id ?? "")
    .trim()
    .toUpperCase();
  const destination = String(data._destinationId ?? data.destination_vertex ?? data.destination ?? data.target?.id ?? "")
    .trim()
    .toUpperCase();

  if (!origin || !destination) return null;
  return { origin, destination };
}

createGraphConfigController({
  statusElement: status,
});

tripSessionPanel.setAvailability({ graphLoaded: false, sessionActive: false });
tripSessionPanel.setBanner("Carga un grafo para iniciar una sesión R3.");

// Small helper button to test the blocked route visual state on the first rendered link.
(() => {
  const controls = document.querySelector("header .controls");
  if (!controls) return;

  const testBtn = document.createElement("button");
  testBtn.id = "btnSimulateBlock";
  testBtn.textContent = "Probar bloqueo";
  controls.appendChild(testBtn);

  testBtn.addEventListener("click", () => {
    const endpoints = getFirstRenderedLinkEndpoints();
    if (!endpoints) {
      status.textContent = "Carga un grafo primero para probar el bloqueo visual.";
      return;
    }

    const { origin, destination } = endpoints;
    const currentlyBlocked = Boolean(document.querySelector(".graph-links .link.link-blocked"));
    const nextBlockedState = !currentlyBlocked;
    const ok = graphUi.markLinkBlocked(origin, destination, nextBlockedState);

    if (ok) {
      flightAnimator.stop();
      if (nextBlockedState) {
        flightAnimator.animateRoute({ originId: origin, destinationId: destination, blocked: true, durationMs: 1400 });
      }
    }

    status.textContent = ok
      ? `Ruta ${origin} → ${destination} ${nextBlockedState ? "marcada como bloqueada" : "desbloqueada"}`
      : `No se pudo actualizar la ruta ${origin} → ${destination}`;
  });
})();

// Session control wired into the trip session panel
let currentSessionId = null;
tripSessionPanel.onStart(async () => {
  // try DOM-selected node first, then fall back to first rendered link endpoints
  let selected = null;
  const selEl = document.querySelector('.graph-nodes .node.node-selected .node-code');
  if (selEl) selected = String(selEl.textContent || '').trim().toUpperCase();
  const endpoints = getFirstRenderedLinkEndpoints();
  const origin = (selected || (endpoints && endpoints.origin) || "").toUpperCase();
  if (!origin) {
    status.textContent = "Selecciona un aeropuerto en el grafo para iniciar la sesión.";
    return;
  }

  const budget = tripSessionPanel.getState().budgetInitial || 1000;
  const timeHours = Math.max(1, Math.round((tripSessionPanel.getState().timeRemainingMin || (72 * 60)) / 60));

  status.textContent = "Iniciando sesión...";
  try {
    const res = await apiPost("/api/session/start", { origin, budget, time_h: timeHours });
    currentSessionId = res.session_id;
    tripSessionPanel.setSessionId(currentSessionId);
    tripSessionPanel.setAvailability({ graphLoaded: true, sessionActive: true });
    tripSessionPanel.setSuggestedRoute(null);
    tripSessionPanel.setRoutePlan([]);
    tripSessionPanel.setOptionalActivitiesVisible(false);
    const meta = res.meta || {};
    tripSessionPanel.setState({
      budgetInitial: tripSessionPanel.getState().budgetInitial,
      budgetRemaining: meta.budget_remaining ?? tripSessionPanel.getState().budgetRemaining,
      timeRemainingMin: meta.time_remaining_min ?? tripSessionPanel.getState().timeRemainingMin,
      freeTimeMin: meta.free_time_min ?? tripSessionPanel.getState().freeTimeMin,
      currentStayRequiredMin: meta.current_stay_required_min ?? tripSessionPanel.getState().currentStayRequiredMin,
      currentOptionalStayMin: meta.current_optional_stay_min ?? tripSessionPanel.getState().currentOptionalStayMin,
    });
    tripSessionPanel.setProposals(res.proposals ?? null);
    tripSessionPanel.setBanner(`Sesión iniciada: ${currentSessionId}. Revisa rutas, actividades y trabajos disponibles.`);
    status.textContent = `Sesión iniciada: ${currentSessionId}`;
  } catch (err) {
    tripSessionPanel.setBanner(`No se pudo iniciar la sesión: ${err.message || err}`, "error");
    status.textContent = `Error iniciando sesión: ${err.message || err}`;
  }
});

tripSessionPanel.onSuggestRoute(async () => {
  if (!currentSessionId) {
    status.textContent = "No hay sesión activa. Inicia una sesión primero.";
    return;
  }
  status.textContent = "Generando ruta sugerida...";
  try {
    const res = await apiPost(`/api/session/${currentSessionId}/suggest-route`, {});
    const meta = res.meta || {};
    tripSessionPanel.setState({
      budgetRemaining: meta.budget_remaining ?? tripSessionPanel.getState().budgetRemaining,
      timeRemainingMin: meta.time_remaining_min ?? tripSessionPanel.getState().timeRemainingMin,
      freeTimeMin: meta.free_time_min ?? tripSessionPanel.getState().freeTimeMin,
      currentStayRequiredMin: meta.current_stay_required_min ?? tripSessionPanel.getState().currentStayRequiredMin,
      currentOptionalStayMin: meta.current_optional_stay_min ?? tripSessionPanel.getState().currentOptionalStayMin,
    });
    tripSessionPanel.setProposals(res.proposals ?? null);
    tripSessionPanel.setSuggestedRoute(res.suggested_route ?? null);
    tripSessionPanel.setRoutePlan(res.route_plan ?? []);
    tripSessionPanel.setOptionalActivitiesVisible(false);

    const routesCount = res.proposals?.routes?.length ?? 0;
    const activitiesCount = res.proposals?.activities?.length ?? 0;
    const jobsCount = res.proposals?.jobs?.length ?? 0;
    const suggestedDestination = res.suggested_route?.destination ?? "sin ruta sugerida";
    tripSessionPanel.setBanner(`Ruta sugerida guardada: ${suggestedDestination}. ${routesCount} rutas, ${activitiesCount} actividades y ${jobsCount} trabajos disponibles.`, "success");
    status.textContent = `Ruta sugerida: ${suggestedDestination}`;
  } catch (err) {
    tripSessionPanel.setBanner(`No se pudo sugerir la ruta: ${err.message || err}`, "error");
    status.textContent = `Error al sugerir ruta: ${err.message || err}`;
  }
});

tripSessionPanel.onChoice(async choice => {
  if (!currentSessionId) {
    status.textContent = "No hay sesión activa. Inicia una sesión primero.";
    return;
  }

  status.textContent = "Aplicando decisión...";
  try {
    const res = await apiPost(`/api/session/${currentSessionId}/choice`, choice);
    const updatedState = res.updated_state ?? {};
    const nextProposals = res.next_proposals ?? null;
    tripSessionPanel.setState({
      budgetRemaining: updatedState.budget_remaining ?? tripSessionPanel.getState().budgetRemaining,
      timeRemainingMin: updatedState.time_remaining_min ?? tripSessionPanel.getState().timeRemainingMin,
      budgetInitial: updatedState.budget_initial ?? tripSessionPanel.getState().budgetInitial,
      freeTimeMin: updatedState.free_time_min ?? tripSessionPanel.getState().freeTimeMin,
      currentStayRequiredMin: updatedState.current_stay_required_min ?? tripSessionPanel.getState().currentStayRequiredMin,
      currentOptionalStayMin: updatedState.current_optional_stay_min ?? tripSessionPanel.getState().currentOptionalStayMin,
    });
    tripSessionPanel.setProposals(nextProposals);
    const remainingPlan = Array.isArray(updatedState.planned_route) ? updatedState.planned_route : [];
    tripSessionPanel.setSuggestedRoute(remainingPlan[0] ?? null);
    tripSessionPanel.setRoutePlan(updatedState.planned_route ?? []);

    if ((choice.kind || "").toLowerCase() === "transport") {
      tripSessionPanel.setOptionalActivitiesVisible(false);
    }

    if (Array.isArray(res.events) && res.events.length) {
      tripSessionPanel.setBanner(`Decisión aplicada. ${res.events[0]}`, "success");
      status.textContent = res.events.join(" | ");
    } else if (Array.isArray(res.errors) && res.errors.length) {
      tripSessionPanel.setBanner(`No se pudo aplicar la decisión: ${res.errors[0]}`, "error");
      status.textContent = res.errors.join(" | ");
    } else {
      tripSessionPanel.setBanner("Decisión aplicada correctamente.", "success");
      status.textContent = "Decisión aplicada correctamente.";
    }
  } catch (err) {
    tripSessionPanel.setBanner(`Error aplicando decisión: ${err.message || err}`, "error");
    status.textContent = `Error aplicando decisión: ${err.message || err}`;
  }
});

tripSessionPanel.onReport(async () => {
  if (!currentSessionId) {
    tripSessionPanel.setBanner("No hay sesión activa para generar un reporte.", "error");
    return;
  }

  tripSessionPanel.setBanner("Generando reporte final...");
  try {
    const res = await apiGet(`/api/session/${currentSessionId}/report`);
    tripSessionPanel.setReport(res.report ?? null);
    tripSessionPanel.setBanner("Reporte final listo. Puedes revisarlo debajo del panel.", "success");
    status.textContent = "Reporte generado correctamente.";
  } catch (err) {
    tripSessionPanel.setBanner(`No se pudo generar el reporte: ${err.message || err}`, "error");
    status.textContent = `Error al generar reporte: ${err.message || err}`;
  }
});

// Load the current backend config so the UI can show the lodging rule consistently.
apiGet("/api/config")
  .then(config => {
    infoPanel.setRules(config ?? {});
    tripSessionPanel.setRules(config ?? {});
  })
  .catch(() => {
    infoPanel.setRules({ intervaloAlojamiento: 20 });
    tripSessionPanel.setRules({ intervaloAlojamiento: 20, intervaloAlimentacion: 8 });
  });

jsonFileInput.addEventListener("change", event => {
  const selectedFile = event.target.files?.[0];
  fileLabel.textContent = selectedFile ? `📂 ${selectedFile.name}` : "Seleccionar archivo .json";
});

document.querySelectorAll(".modal-close[data-close]").forEach(button => {
  button.addEventListener("click", () => closeModal());
});

jsonModal.addEventListener("click", event => {
  if (event.target === jsonModal) closeModal();
});

document.getElementById("btnLoadSample").addEventListener("click", openModal);

document.getElementById("loadJsonConfirmBtn").addEventListener("click", async () => {
  const file = jsonFileInput.files?.[0];
  if (!file) {
    status.textContent = "Selecciona un archivo JSON primero.";
    return;
  }

  status.textContent = "Cargando JSON...";

  const formData = new FormData();
  formData.append("file", file);

  const response = await apiPostFormData("/api/load-graph", formData);
  const d3Graph = transformGraphToD3Data(response.graph ?? response);

  flightAnimator.stop();
  graphUi.renderGraph(d3Graph, "graphSvg", "graphContainer");
  infoPanel.clear();
  tripSessionPanel.setState({
    budgetInitial: 1000,
    budgetRemaining: 1000,
    timeRemainingMin: 72 * 60,
    freeTimeMin: 0,
    currentStayRequiredMin: 0,
    currentOptionalStayMin: 0,
  });
  tripSessionPanel.setSessionId(null);
  tripSessionPanel.clearProposals();
  tripSessionPanel.setReport(null);
  tripSessionPanel.setSuggestedRoute(null);
  tripSessionPanel.setRoutePlan([]);
  tripSessionPanel.setOptionalActivitiesVisible(false);
  tripSessionPanel.setAvailability({ graphLoaded: true, sessionActive: false });
  tripSessionPanel.setBanner("Grafo cargado. Ahora puedes iniciar una sesión R3.", "success");
  infoPanel.setRules(await apiGet("/api/config").catch(() => ({ intervaloAlojamiento: 20 })));
  tripSessionPanel.setRules(await apiGet("/api/config").catch(() => ({ intervaloAlojamiento: 20, intervaloAlimentacion: 8 })));
  status.textContent = `Grafo cargado: ${response.airports ?? d3Graph.nodes.length} aeropuertos.`;
  closeModal();
});