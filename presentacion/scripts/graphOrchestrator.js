import { apiGet, apiPost, apiPostFormData } from "./api/client.js";
import { createGraphUi, transformGraphToD3Data } from "./graphUI.js";
import { FlightAnimator } from "./flightAnimator.js";
import { createInfoPanel } from "./panels/infoPanel.js";
import { createTripSessionPanel } from "./panels/tripSessionPanel.js";
import { createPlannerPanel } from "./panels/planner-panel.js";
import { createGraphConfigController } from "./graphConfigController.js";
import { createRouteBlockingController } from "./routeBlockingController.js";

const status = document.getElementById("status");
const jsonModal = document.getElementById("jsonModal");
const jsonFileInput = document.getElementById("jsonFile");
const fileLabel = document.getElementById("fileLabel");
const infoPanel = createInfoPanel({ panelId: "airportInfoPanel" });
const tripSessionPanel = createTripSessionPanel({ panelId: "tripSessionPanel" });
const configController = createGraphConfigController({
  statusElement: status,
});
const plannerPanel = createPlannerPanel({ panelId: "plannerPanel" });

function setStatusMessage(message, kind = "info") {
  const text = String(message ?? "");
  status.textContent = text;

  const alertPattern = /aliment|comid|meal|food|hosped|aloj|lodging/i;
  if (kind === "error" || alertPattern.test(text)) {
    status.dataset.kind = kind === "error" ? "error" : "alert";
  } else {
    delete status.dataset.kind;
  }
}

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
const routeBlockingController = createRouteBlockingController({
  apiPost,
  graphUi,
  flightAnimator,
  infoPanel,
  tripSessionPanel,
  setStatusMessage,
});

const {
  getBlockedRoutes,
  clearBlockedRoutes,
  isRouteBlocked,
  interruptRoute,
  setGraphData,
} = routeBlockingController;

function syncConfigControls() {
  if (configController?.refreshControls) {
    return configController.refreshControls();
  }
  return Promise.resolve();
}

tripSessionPanel.setAvailability({ graphLoaded: false, sessionActive: false });
tripSessionPanel.setBanner("Restaurando el grafo guardado...");
void syncConfigControls();

// Session control wired into the trip session panel
let currentSessionId = null;
let pendingTransportChoice = null;

function resetSessionUi(message = "Sesión cancelada.") {
  pendingTransportChoice = null;
  flightAnimator.stop();
  currentSessionId = null;
  tripSessionPanel.setSessionId(null);
  tripSessionPanel.setAvailability({ graphLoaded: true, sessionActive: false });
  tripSessionPanel.setSuggestedRoute(null);
  tripSessionPanel.setRoutePlan([]);
  tripSessionPanel.setOptionalActivitiesVisible(false);
  tripSessionPanel.clearProposals();
  tripSessionPanel.setBlockedRoutes(getBlockedRoutes());
  tripSessionPanel.setBanner(message);
  setStatusMessage(message);
  void syncConfigControls();
}

async function closeCurrentSession() {
  if (!currentSessionId) return;

  await apiPost(`/api/session/${currentSessionId}/close`, {});
}

async function applySessionChoice(choice) {
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
    currentAirportId: updatedState.current_airport ?? tripSessionPanel.getState().currentAirportId,
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
    setStatusMessage(res.events.join(" | "));
  } else if (Array.isArray(res.errors) && res.errors.length) {
    tripSessionPanel.setBanner(`No se pudo aplicar la decisión: ${res.errors[0]}`, "error");
    setStatusMessage(res.errors.join(" | "), "error");
  } else {
    tripSessionPanel.setBanner("Decisión aplicada correctamente.", "success");
    setStatusMessage("Decisión aplicada correctamente.");
  }

  void syncConfigControls();

  return res;
}

flightAnimator.onRouteFinished(async ({ status } = {}) => {
  if (!pendingTransportChoice) return;

  const pending = pendingTransportChoice;
  pendingTransportChoice = null;

  if (!currentSessionId || pending.sessionId !== currentSessionId) {
    return;
  }

  if (status === "returned") {
    tripSessionPanel.setBanner("Ruta bloqueada durante el trayecto. Se mantiene el aeropuerto de origen y sus opciones.", "info");
    setStatusMessage("Ruta bloqueada: regreso al origen. No se aplicó cambio de destino.", "info");
    return;
  }

  try {
    setStatusMessage("Llegaste al destino. Aplicando decisión de transporte...");
    await applySessionChoice(pending.choice);
  } catch (err) {
    tripSessionPanel.setBanner(`Error aplicando decisión al llegar: ${err.message || err}`, "error");
    setStatusMessage(`Error aplicando decisión al llegar: ${err.message || err}`, "error");
  }
});

async function startSessionFromUi() {
  // Try DOM-selected node first
  let selected = null;
  const selEl = document.querySelector('.graph-nodes .node.node-selected .node-code');
  if (selEl) selected = String(selEl.textContent || '').trim().toUpperCase();
  const origin = selected || "";
  if (!origin) {
    setStatusMessage("Selecciona un aeropuerto en el grafo para iniciar la sesión.");
    return;
  }

  const budget = tripSessionPanel.getState().budgetInitial || 1000;
  const timeHours = Math.max(1, Math.round((tripSessionPanel.getState().timeRemainingMin || (72 * 60)) / 60));

  setStatusMessage("Iniciando sesión...");
  try {
    const res = await apiPost("/api/session/start", { origin, budget, time_h: timeHours });
    currentSessionId = res.session_id;
    tripSessionPanel.setSessionId(currentSessionId);
    tripSessionPanel.setAvailability({ graphLoaded: true, sessionActive: true });
    const meta = res.meta || {};
    tripSessionPanel.setState({
      budgetInitial: tripSessionPanel.getState().budgetInitial,
      budgetRemaining: meta.budget_remaining ?? tripSessionPanel.getState().budgetRemaining,
      timeRemainingMin: meta.time_remaining_min ?? tripSessionPanel.getState().timeRemainingMin,
      freeTimeMin: meta.free_time_min ?? tripSessionPanel.getState().freeTimeMin,
      currentStayRequiredMin: meta.current_stay_required_min ?? tripSessionPanel.getState().currentStayRequiredMin,
      currentOptionalStayMin: meta.current_optional_stay_min ?? tripSessionPanel.getState().currentOptionalStayMin,
      currentAirportId: meta.current_airport ?? tripSessionPanel.getState().currentAirportId,
    });
    tripSessionPanel.setSuggestedRoute(null);
    tripSessionPanel.setRoutePlan([]);
    tripSessionPanel.setOptionalActivitiesVisible(false);
    tripSessionPanel.setProposals(res.proposals ?? null);
    tripSessionPanel.setBlockedRoutes(getBlockedRoutes());
    tripSessionPanel.setBanner(`Sesión iniciada: ${currentSessionId}. Revisa rutas, actividades y trabajos disponibles.`);
    setStatusMessage(`Sesión iniciada: ${currentSessionId}`);
    void syncConfigControls();
  } catch (err) {
    tripSessionPanel.setBanner(`No se pudo iniciar la sesión: ${err.message || err}`, "error");
    setStatusMessage(`Error iniciando sesión: ${err.message || err}`, "error");
  }
}

tripSessionPanel.onToggleSession(async () => {
  if (currentSessionId) {
    try {
      setStatusMessage("Cerrando sesión...");
      await closeCurrentSession();
      resetSessionUi("Sesión cancelada.");
    } catch (err) {
      tripSessionPanel.setBanner(`No se pudo cerrar la sesión: ${err.message || err}`, "error");
      setStatusMessage(`No se pudo cerrar la sesión: ${err.message || err}`, "error");
    }
    return;
  }

  await startSessionFromUi();
});

tripSessionPanel.onSuggestRoute(async () => {
  if (!currentSessionId) {
    setStatusMessage("No hay sesión activa. Inicia una sesión primero.");
    return;
  }
  setStatusMessage("Generando ruta sugerida...");
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
    tripSessionPanel.setBlockedRoutes(getBlockedRoutes());
    void syncConfigControls();

    const routesCount = res.proposals?.routes?.length ?? 0;
    const activitiesCount = res.proposals?.activities?.length ?? 0;
    const jobsCount = res.proposals?.jobs?.length ?? 0;
    const suggestedDestination = res.suggested_route?.destination ?? "sin ruta sugerida";
    tripSessionPanel.setBanner(`Ruta sugerida guardada: ${suggestedDestination}. ${routesCount} rutas, ${activitiesCount} actividades y ${jobsCount} trabajos disponibles.`, "success");
    setStatusMessage(`Ruta sugerida: ${suggestedDestination}`);
  } catch (err) {
    tripSessionPanel.setBanner(`No se pudo sugerir la ruta: ${err.message || err}`, "error");
    setStatusMessage(`Error al sugerir ruta: ${err.message || err}`, "error");
  }
});

tripSessionPanel.onCancelSuggestedRoute(() => {
  tripSessionPanel.setSuggestedRoute(null);
  tripSessionPanel.setRoutePlan([]);
  tripSessionPanel.setBanner("Ruta sugerida cancelada.");
  setStatusMessage("Ruta sugerida cancelada.");
  void syncConfigControls();
});

plannerPanel.onHighlightRoute((itinerary) => {
  // itinerary.legs tiene [{origin_id, destination_id, ...}
  const edgeList = itinerary.legs.map(l => ({
    source: l.origin_id,
    target: l.destination_id,
  }));
  graphUi.highlightRoute(edgeList); 
});

tripSessionPanel.onChoice(async choice => {
  if (!currentSessionId) {
    setStatusMessage("No hay sesión activa. Inicia una sesión primero.");
    return;
  }

  if (pendingTransportChoice) {
    setStatusMessage("Hay un vuelo en curso. Espera a que llegue o se devuelva para aplicar otra decisión.", "info");
    return;
  }

  const originAirport = tripSessionPanel.getState().currentAirportId || choice.origin || null;
  const isTransport = (choice.kind || "").toLowerCase() === "transport";

  if (isTransport && originAirport && choice.destination) {
    const routeIsBlocked = choice.blocked || isRouteBlocked(originAirport, choice.destination);
    if (routeIsBlocked) {
      interruptRoute(originAirport, choice.destination, true, "adverse-situation").catch(() => {});
      setStatusMessage("La ruta está bloqueada. No se inicia el desplazamiento.", "info");
      return;
    }

    pendingTransportChoice = {
      choice,
      sessionId: currentSessionId,
    };

    tripSessionPanel.setOptionalActivitiesVisible(false);
    tripSessionPanel.setBanner(`Vuelo en curso ${originAirport} → ${choice.destination}. Las opciones se actualizarán al llegar.`, "info");
    setStatusMessage(`Vuelo en curso: ${originAirport} → ${choice.destination}`);

    flightAnimator.stop();
    flightAnimator.animateRoute({
      originId: originAirport,
      destinationId: choice.destination,
      blocked: false,
    });
    return;
  }

  setStatusMessage("Aplicando decisión...");
  try {
    await applySessionChoice(choice);
  } catch (err) {
    tripSessionPanel.setBanner(`Error aplicando decisión: ${err.message || err}`, "error");
    setStatusMessage(`Error aplicando decisión: ${err.message || err}`, "error");
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

async function restorePersistedGraph() {
  try {
    const response = await apiGet("/api/current-graph");
    const savedGraph = response?.graph ?? null;
    if (!savedGraph || !Array.isArray(savedGraph.vertices) || !savedGraph.vertices.length) {
      tripSessionPanel.setBanner("Carga un grafo para iniciar una sesión R3.");
      return;
    }

    const d3Graph = transformGraphToD3Data(savedGraph);
    flightAnimator.stop();
    clearBlockedRoutes();
    setGraphData(d3Graph);
    graphUi.renderGraph(d3Graph, "graphSvg", "graphContainer");
    document.getElementById("rightPanels")?.classList.remove("hidden");
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
    tripSessionPanel.setSuggestedRoute(null);
    tripSessionPanel.setRoutePlan([]);
    tripSessionPanel.setOptionalActivitiesVisible(false);
    tripSessionPanel.setBlockedRoutes(getBlockedRoutes());
    tripSessionPanel.setAvailability({ graphLoaded: true, sessionActive: false });
    tripSessionPanel.setBanner("Grafo restaurado desde almacenamiento local.", "success");
    infoPanel.setRules(await apiGet("/api/config").catch(() => ({ intervaloAlojamiento: 20 })));
    tripSessionPanel.setRules(await apiGet("/api/config").catch(() => ({ intervaloAlojamiento: 20, intervaloAlimentacion: 8 })));
    setStatusMessage(`Grafo restaurado: ${response.airports ?? d3Graph.nodes.length} aeropuertos.`);
  } catch (err) {
    tripSessionPanel.setBanner("Carga un grafo para iniciar una sesión R3.");
    setStatusMessage(`No se pudo restaurar el grafo guardado: ${err.message || err}`, "error");
  }
}

void restorePersistedGraph();

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
    setStatusMessage("Selecciona un archivo JSON primero.");
    return;
  }

  setStatusMessage("Cargando JSON...");

  const formData = new FormData();
  formData.append("file", file);

  const response = await apiPostFormData("/api/load-graph", formData);
  const d3Graph = transformGraphToD3Data(response.graph ?? response);

  flightAnimator.stop();
  clearBlockedRoutes();
  setGraphData(d3Graph);
  graphUi.renderGraph(d3Graph, "graphSvg", "graphContainer");
  document.getElementById("rightPanels")?.classList.remove("hidden");
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
  tripSessionPanel.setSuggestedRoute(null);
  tripSessionPanel.setRoutePlan([]);
  tripSessionPanel.setOptionalActivitiesVisible(false);
  tripSessionPanel.setBlockedRoutes(getBlockedRoutes());
  tripSessionPanel.setAvailability({ graphLoaded: true, sessionActive: false });
  plannerPanel.setAvailability({ graphLoaded: true });
  tripSessionPanel.setBanner("Grafo cargado con exito", "success");
  infoPanel.setRules(await apiGet("/api/config").catch(() => ({ intervaloAlojamiento: 20 })));
  tripSessionPanel.setRules(await apiGet("/api/config").catch(() => ({ intervaloAlojamiento: 20, intervaloAlimentacion: 8 })));
  setStatusMessage(`Grafo cargado: ${response.airports ?? d3Graph.nodes.length} aeropuertos.`);
  closeModal();
});

// Budget change handler: propagate to server when session active
tripSessionPanel.onBudgetChange(async newBudget => {
  const parsed = Number(newBudget);
  if (!Number.isFinite(parsed) || parsed < 0) return;
  if (!currentSessionId) {
    // No session: keep local values already set by panel
    return;
  }

  setStatusMessage("Actualizando presupuesto...");
  try {
    const res = await apiPost(`/api/session/${currentSessionId}/update-budget`, { budget: parsed });
    const meta = res.meta || {};
    tripSessionPanel.setState({
      budgetInitial: meta.budget_initial ?? tripSessionPanel.getState().budgetInitial,
      budgetRemaining: meta.budget_remaining ?? tripSessionPanel.getState().budgetRemaining,
    });
    tripSessionPanel.setProposals(res.proposals ?? null);
    tripSessionPanel.setBanner(`Presupuesto actualizado: $${parsed.toFixed(2)}`, "success");
    setStatusMessage("Presupuesto actualizado.");
  } catch (err) {
    tripSessionPanel.setBanner(`No se pudo actualizar el presupuesto: ${err.message || err}`, "error");
    setStatusMessage(`Error actualizando presupuesto: ${err.message || err}`, "error");
  }
});