// =============================================================================
//  Airport Info Panel
//  Responsibility: render selected airport details in a dedicated side panel.
// =============================================================================

function collectRouteSummaries(adjacencies = []) {
  const summaries = [];

  adjacencies.forEach(route => {
    if (!route || typeof route !== "object") return;

    const destination = route.destination_vertex ?? route.destination_id ?? route.target ?? route.destination_code ?? route.destination ?? route.to ?? "-";
    const aircrafts = route.aircrafts ?? route.aircraft ?? [];
    const aircraftTypes = Array.isArray(aircrafts)
      ? aircrafts.filter(type => typeof type === "string" && type.trim()).map(type => type.trim())
      : typeof aircrafts === "string" && aircrafts.trim()
        ? [aircrafts.trim()]
        : [];

    summaries.push({
      destination,
      aircraftTypes,
    });
  });

  return summaries;
}

export function createInfoPanel({ panelId = "airportInfoPanel" } = {}) {
  const panel = document.getElementById(panelId);

  if (!panel) {
    throw new Error(`Info panel with id ${panelId} was not found.`);
  }

  const codeEl = panel.querySelector("#infoCode");
  const nameEl = panel.querySelector("#infoName");
  const cityEl = panel.querySelector("#infoCity");
  const countryEl = panel.querySelector("#infoCountry");
  const timezoneEl = panel.querySelector("#infoTimezone");
  const airlinesEl = panel.querySelector("#infoAirlines");

  function show(node) {
    if (!node || typeof node !== "object") return;

    // Use logical OR to treat empty strings as missing values
    const airportCode = node.code || node.airport_code || node.iata || node.id || "-";
    const airportName = node.name || "-";
    const city = node.city || node.name || "-";
    const country = node.country || "-";
    const timezone = node.timezone || "-";
    const routeSummaries = collectRouteSummaries(node.adjacencies ?? []);

    codeEl.textContent = airportCode;
    nameEl.textContent = airportName;
    cityEl.textContent = city;
    countryEl.textContent = country;
    timezoneEl.textContent = timezone;

    airlinesEl.innerHTML = "";
    if (!routeSummaries.length) {
      const li = document.createElement("li");
      li.textContent = "Sin rutas salientes";
      airlinesEl.appendChild(li);
    } else {
      routeSummaries.forEach(route => {
        const li = document.createElement("li");
        const aircraftLabel = route.aircraftTypes.length ? route.aircraftTypes.join(", ") : "Sin aeronave";
        li.textContent = `${route.destination}: ${aircraftLabel}`;
        airlinesEl.appendChild(li);
      });
    }

    panel.classList.remove("hidden");
  }

  function clear() {
    codeEl.textContent = "-";
    nameEl.textContent = "-";
    cityEl.textContent = "-";
    countryEl.textContent = "-";
    timezoneEl.textContent = "-";
    airlinesEl.innerHTML = "";
    panel.classList.add("hidden");
  }

  return {
    show,
    clear,
  };
}
