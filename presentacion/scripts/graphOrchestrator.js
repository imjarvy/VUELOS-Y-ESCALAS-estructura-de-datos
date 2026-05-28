import { apiGet, apiPostFormData } from "./api/client.js";
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
  });
  infoPanel.setRules(await apiGet("/api/config").catch(() => ({ intervaloAlojamiento: 20 })));
  tripSessionPanel.setRules(await apiGet("/api/config").catch(() => ({ intervaloAlojamiento: 20, intervaloAlimentacion: 8 })));
  status.textContent = `Grafo cargado: ${response.airports ?? d3Graph.nodes.length} aeropuertos.`;
  closeModal();
});