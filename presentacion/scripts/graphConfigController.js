import { apiGet, apiPost } from "./api/client.js";

export function createGraphConfigController({ statusElement = null } = {}) {
  const configModal = document.getElementById("configModal");
  const openButton = document.getElementById("btnOpenConfig");
  const cancelButton = document.getElementById("cancelConfigBtn");
  const saveButton = document.getElementById("saveConfigBtn");

  const fields = {
    budgetThreshold: document.getElementById("cfgBudgetThresholdPct"),
    lodgingInterval: document.getElementById("cfgLodgingIntervalH"),
    mealInterval: document.getElementById("cfgMealIntervalH"),
    subsidizedDistance: document.getElementById("cfgMaxSubsidizedDistanceFrac"),
    commercialCost: document.getElementById("cfgCommercialCostPerKm"),
    commercialTime: document.getElementById("cfgCommercialTimePerKmMin"),
    regionalCost: document.getElementById("cfgRegionalCostPerKm"),
    regionalTime: document.getElementById("cfgRegionalTimePerKmMin"),
    propellerCost: document.getElementById("cfgPropellerCostPerKm"),
    propellerTime: document.getElementById("cfgPropellerTimePerKmMin"),
  };

  let currentConfig = null;

  function setStatus(message) {
    if (statusElement) {
      statusElement.textContent = message;
    }
  }

  function openModal() {
    configModal.classList.remove("hidden");
  }

  function closeModal() {
    configModal.classList.add("hidden");
  }

  function fillForm(config) {
    const aeronaves = config?.aeronaves ?? {};

    fields.budgetThreshold.value = config?.presupuestoMinimoPorc ?? 35;
    fields.lodgingInterval.value = config?.intervaloAlojamiento ?? 20;
    fields.mealInterval.value = config?.intervaloAlimentacion ?? 8;
    fields.subsidizedDistance.value = config?.max_subsidized_distance_frac ?? 0.2;

    fields.commercialCost.value = aeronaves.commercial?.costoKm ?? 0.18;
    fields.commercialTime.value = aeronaves.commercial?.tiempoKm ?? 0.7;
    fields.regionalCost.value = aeronaves.regional?.costoKm ?? 0.25;
    fields.regionalTime.value = aeronaves.regional?.tiempoKm ?? 1.1;
    fields.propellerCost.value = aeronaves.propeller?.costoKm ?? 0.12;
    fields.propellerTime.value = aeronaves.propeller?.tiempoKm ?? 2.5;
  }

  function readForm() {
    return {
      aeronaves: {
        commercial: {
          costoKm: Number(fields.commercialCost.value),
          tiempoKm: Number(fields.commercialTime.value),
        },
        regional: {
          costoKm: Number(fields.regionalCost.value),
          tiempoKm: Number(fields.regionalTime.value),
        },
        propeller: {
          costoKm: Number(fields.propellerCost.value),
          tiempoKm: Number(fields.propellerTime.value),
        },
      },
      presupuestoMinimoPorc: Number(fields.budgetThreshold.value),
      intervaloAlojamiento: Number(fields.lodgingInterval.value),
      intervaloAlimentacion: Number(fields.mealInterval.value),
      max_subsidized_distance_frac: Number(fields.subsidizedDistance.value),
    };
  }

  async function loadConfig() {
    const config = await apiGet("/api/config");
    currentConfig = config;
    fillForm(config);
    return config;
  }

  async function saveConfig() {
    const payload = readForm();
    const response = await apiPost("/api/config", payload);
    currentConfig = response.config ?? payload;
    fillForm(currentConfig);
    return response;
  }

  if (openButton) {
    openButton.addEventListener("click", async () => {
      setStatus("Cargando configuración...");
      await loadConfig();
      setStatus("Configuración lista.");
      openModal();
    });
  }

  if (cancelButton) {
    cancelButton.addEventListener("click", () => closeModal());
  }

  if (saveButton) {
    saveButton.addEventListener("click", async () => {
      setStatus("Guardando configuración...");
      await saveConfig();
      setStatus("Configuración guardada.");
      closeModal();
    });
  }

  if (configModal) {
    configModal.addEventListener("click", event => {
      if (event.target === configModal) closeModal();
    });
  }

  return {
    loadConfig,
    saveConfig,
    openModal,
    closeModal,
    getCurrentConfig: () => currentConfig,
  };
}
