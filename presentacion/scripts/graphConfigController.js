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
  let currentLockState = { locked: false, active_session_count: 0, active_route_count: 0, message: "" };

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

  function applyControlState() {
    const locked = Boolean(currentLockState?.locked);
    if (openButton) {
      openButton.disabled = locked;
      openButton.title = locked ? currentLockState.message : "";
    }
    if (saveButton) {
      saveButton.disabled = locked;
      saveButton.title = locked ? currentLockState.message : "";
    }
  }

  async function loadLockState() {
    // The backend decides whether config editing is allowed.
    const lockState = await apiGet("/api/config/status");
    currentLockState = {
      locked: Boolean(lockState?.locked),
      active_session_count: Number(lockState?.active_session_count ?? 0),
      active_route_count: Number(lockState?.active_route_count ?? 0),
      message: String(lockState?.message ?? ""),
    };
    applyControlState();
    return currentLockState;
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
    // Populate the modal with the active graph configuration.
    const config = await apiGet("/api/config");
    currentConfig = config;
    fillForm(config);
    return config;
  }

  async function saveConfig() {
    // Re-check the lock before sending an update.
    const lockState = await loadLockState();
    if (lockState.locked) {
      throw new Error(lockState.message || "No puedes cambiar la configuración mientras haya una sesión o ruta activa.");
    }

    const payload = readForm();
    const response = await apiPost("/api/config", payload);
    currentConfig = response.config ?? payload;
    fillForm(currentConfig);
    return response;
  }

  if (openButton) {
    openButton.addEventListener("click", async () => {
      try {
        setStatus("Verificando estado de la configuración...");
        const lockState = await loadLockState();
        if (lockState.locked) {
          setStatus(lockState.message || "No puedes cambiar la configuración mientras haya una sesión activa.");
          return;
        }

        setStatus("Cargando configuración...");
        await loadConfig();
        setStatus("Configuración lista.");
        openModal();
      } catch (error) {
        setStatus(error.message || "No se pudo cargar la configuración.");
      }
    });
  }

  if (cancelButton) {
    cancelButton.addEventListener("click", () => closeModal());
  }

  if (saveButton) {
    saveButton.addEventListener("click", async () => {
      try {
        setStatus("Guardando configuración...");
        await saveConfig();
        setStatus("Configuración guardada.");
        closeModal();
      } catch (error) {
        setStatus(error.message || "No se pudo guardar la configuración.");
      }
    });
  }

  if (configModal) {
    configModal.addEventListener("click", event => {
      if (event.target === configModal) closeModal();
    });
  }

  void loadLockState().catch(() => {
    applyControlState();
  });

  return {
    loadConfig,
    loadLockState,
    saveConfig,
    openModal,
    closeModal,
    refreshControls: loadLockState,
    getCurrentConfig: () => currentConfig,
  };
}
