import { apiGet, apiPost, apiPostFormData } from "./api/client.js";
import { createGraphUi, transformGraphToD3Data } from "./graphUI.js";
import { FlightAnimator } from "./flightAnimator.js";
import { createInfoPanel } from "./panels/infoPanel.js";
import { createTripSessionPanel } from "./panels/tripSessionPanel.js";
import { createPlannerPanel } from "./panels/planner/planner-panel.js";
import { createReportPanel } from "./panels/report/report-panel.js";
import { legsToEdgeList } from "./panels/report/report-utils.js";
import { createGraphConfigController } from "./graphConfigController.js";
import { createRouteBlockingController } from "./routeBlockingController.js";
import { createRouteAnimationController } from "./routeAnimationController.js";

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
const reportPanel = createReportPanel({ panelId: "reportPanel" });

function setStatusMessage(message, kind = "info") {
  // Mirror important events in the global status bar.
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
  // Open the JSON upload modal.
  jsonModal.classList.remove("hidden");
}

function closeModal() {
  // Close the JSON upload modal.
  jsonModal.classList.add("hidden");
}

function showGraphPanels() {
  // Reveal the right-side panels once a graph is available.
  document.getElementById("rightPanels")?.classList.remove("hidden");
  document.getElementById("plannerPanel")?.classList.remove("hidden");
  reportPanel?.show?.();
}

const graphUi = createGraphUi({
  state: { selectedCode: null },
  onNodeSelect: node => {
    infoPanel.show(node);
  },
});

const flightAnimator = new FlightAnimator({ svgId: "graphSvg" });
const routeAnimationController = createRouteAnimationController({
  graphUi,
  flightAnimator,
  legsToEdgeList,
});
const routeBlockingController = createRouteBlockingController({
  apiPost,
  graphUi,
  routeAnimationController,
  plannerPanel,
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
  // Refresh configuration widgets so they stay aligned with the backend.
  if (configController?.refreshControls) {
    return configController.refreshControls();
  }
  return Promise.resolve();
}

tripSessionPanel.setAvailability({ graphLoaded: false, sessionActive: false });
void syncConfigControls();

// Session state is coordinated through the trip session panel and the backend session endpoints.
let currentSessionId = null;
let pendingTransportChoice = null;
const {
  playHighlightedRoute,
  stop: stopRouteAnimation,
} = routeAnimationController;

function resetSessionUi(message = "Sesión cancelada.") {
  // Clear all session-specific UI state after a session ends.
  pendingTransportChoice = null;
  stopRouteAnimation();
  currentSessionId = null;
  tripSessionPanel.setSessionId(null);
  reportPanel.setSessionId(null);
  reportPanel.clear();
  reportPanel.setAvailability({ sessionActive: false });
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
  // Notify the backend that the current session should be closed.
  if (!currentSessionId) return;

  await apiPost(`/api/session/${currentSessionId}/close`, {});
}

async function applySessionChoice(choice) {
  // Send the selected action to the backend and refresh the UI with the response.
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
  // Wait for the animated flight to finish before applying the transport choice.
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
  // Start a new trip session using the currently selected airport and panel values.
  // Prefer the currently selected node in the graph if one exists.
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
    reportPanel.setSessionId(currentSessionId);
    reportPanel.setAvailability({ sessionActive: true });
    reportPanel.show();
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
    reportPanel.loadReport(currentSessionId, { quiet: true });
  } catch (err) {
    tripSessionPanel.setBanner(`No se pudo iniciar la sesión: ${err.message || err}`, "error");
    setStatusMessage(`Error iniciando sesión: ${err.message || err}`, "error");
  }
}

tripSessionPanel.onToggleSession(async () => {
  // Toggle the advanced planner session from the panel button.
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
  // Ask the backend for the next suggested route and display it in the panel.
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
  // Clear the current suggested route from the panel.
  tripSessionPanel.setSuggestedRoute(null);
  tripSessionPanel.setRoutePlan([]);
  tripSessionPanel.setBanner("Ruta sugerida cancelada.");
  setStatusMessage("Ruta sugerida cancelada.");
  void syncConfigControls();
});

plannerPanel.onHighlightRoute((itinerary) => {
  // Highlight the full itinerary selected from the planner panel.
  playHighlightedRoute(itinerary?.legs ?? [], { suppressFinishCallback: true });
});

reportPanel.onHighlightRoute((report) => {
  // Highlight the completed route shown in the report panel.
  if (!report?.legs?.length) {
    graphUi.clearRouteHighlight();
    return;
  }
  graphUi.highlightRoute(legsToEdgeList(report.legs));
});

tripSessionPanel.onChoice(async choice => {
  // Apply the selected transport, activity, or job choice.
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

    playHighlightedRoute([
      {
        origin_id: originAirport,
        destination_id: choice.destination,
      },
    ], { suppressFinishCallback: false });
    return;
  }

  setStatusMessage("Aplicando decisión...");
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
      setStatusMessage(res.events.join(" | "));
    } else if (Array.isArray(res.errors) && res.errors.length) {
      tripSessionPanel.setBanner(`No se pudo aplicar la decisión: ${res.errors[0]}`, "error");
      setStatusMessage(res.errors.join(" | "), "error");
    } else {
      tripSessionPanel.setBanner("Decisión aplicada correctamente.", "success");
      setStatusMessage("Decisión aplicada correctamente.");
    }
    reportPanel.loadReport(currentSessionId, { quiet: true });
  } catch (err) {
    tripSessionPanel.setBanner(`Error aplicando decisión: ${err.message || err}`, "error");
    setStatusMessage(`Error aplicando decisión: ${err.message || err}`, "error");
  }
});

// Load the current backend config so the panels stay aligned with the same rules.
apiGet("/api/config")
  .then(config => {
    // Load the active configuration into both the info panel and session panel.
    infoPanel.setRules(config ?? {});
    tripSessionPanel.setRules(config ?? {});
  })
  .catch(() => {
    infoPanel.setRules({ intervaloAlojamiento: 20 });
    tripSessionPanel.setRules({ intervaloAlojamiento: 20, intervaloAlimentacion: 8 });
  });

async function restorePersistedGraph() {
  // Restore the last saved graph and rebuild the UI around it.
  try {
    const response = await apiGet("/api/current-graph");
    const savedGraph = response?.graph ?? null;
    if (!savedGraph || !Array.isArray(savedGraph.vertices) || !savedGraph.vertices.length) {
      // Nothing persisted yet, so the UI stays in the initial empty state.
      tripSessionPanel.setBanner("Carga un grafo para iniciar una sesión R3.");
      return;
    }

    const d3Graph = transformGraphToD3Data(savedGraph);
    stopRouteAnimation();
    clearBlockedRoutes();
    setGraphData(d3Graph);
    graphUi.renderGraph(d3Graph, "graphSvg", "graphContainer");
    showGraphPanels();
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
  button.addEventListener("click", event => {
    // Close the upload or config modal when the user clicks a close button.
    const targetModalId = event.currentTarget?.dataset?.close;
    if (targetModalId === "jsonModal") {
      closeModal();
    } else if (targetModalId === "configModal") {
      configController.closeModal();
    }
  });
});

jsonModal.addEventListener("click", event => {
  // Close the modal when the backdrop itself is clicked.
  if (event.target === jsonModal) closeModal();
});

document.getElementById("btnLoadSample").addEventListener("click", openModal);

document.getElementById("loadJsonConfirmBtn").addEventListener("click", async () => {
  // Load the selected JSON file and rebuild the graph view.
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

  stopRouteAnimation();
  clearBlockedRoutes();
  setGraphData(d3Graph);
  graphUi.renderGraph(d3Graph, "graphSvg", "graphContainer");
  document.getElementById("rightPanels")?.classList.remove("hidden");
  document.getElementById("plannerPanel")?.classList.remove("hidden");
  document.getElementById("reportPanel")?.classList.remove("hidden");
  reportPanel.clear();
  reportPanel.setAvailability({ sessionActive: false });
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
  // Persist budget changes immediately when a session is active.
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