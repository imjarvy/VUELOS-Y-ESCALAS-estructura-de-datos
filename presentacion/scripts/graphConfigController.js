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

  const fallbackConfig = {
    presupuestoMinimoPorc: 35,
    intervaloAlojamiento: 20,
    intervaloAlimentacion: 8,
    max_subsidized_distance_frac: 0.2,
    aeronaves: {
      commercial: { costoKm: 0.18, tiempoKm: 0.7 },
      regional: { costoKm: 0.25, tiempoKm: 1.1 },
      propeller: { costoKm: 0.12, tiempoKm: 2.5 },
    },
  };

  let currentConfig = null;
  let currentLockState = { locked: false, active_session_count: 0, active_route_count: 0, message: "" };

  function setStatus(message) {
    if (statusElement) {
      statusElement.textContent = message;
    }
  }

  function openModal() {
    configModal.hidden = false;
    configModal.classList.remove("hidden");
  }

  function closeModal() {
    configModal.hidden = true;
    configModal.classList.add("hidden");
  }

  function normalizeConfig(config = {}) {
    const source = config && typeof config === "object" && config.config && typeof config.config === "object"
      ? config.config
      : config;

    const aeronaves = source?.aeronaves && typeof source.aeronaves === "object"
      ? source.aeronaves
      : {};

    return {
      ...fallbackConfig,
      ...source,
      aeronaves: {
        ...fallbackConfig.aeronaves,
        commercial: {
          ...fallbackConfig.aeronaves.commercial,
          ...(aeronaves.commercial && typeof aeronaves.commercial === "object" ? aeronaves.commercial : {}),
        },
        regional: {
          ...fallbackConfig.aeronaves.regional,
          ...(aeronaves.regional && typeof aeronaves.regional === "object" ? aeronaves.regional : {}),
        },
        propeller: {
          ...fallbackConfig.aeronaves.propeller,
          ...(aeronaves.propeller && typeof aeronaves.propeller === "object" ? aeronaves.propeller : {}),
        },
      },
    };
  }

  function readNumberField(input, fallback) {
    const parsed = Number(input?.value);
    return Number.isFinite(parsed) ? parsed : fallback;
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
    const normalizedConfig = normalizeConfig(config);
    const aeronaves = normalizedConfig.aeronaves ?? {};

    fields.budgetThreshold.value = normalizedConfig.presupuestoMinimoPorc;
    fields.lodgingInterval.value = normalizedConfig.intervaloAlojamiento;
    fields.mealInterval.value = normalizedConfig.intervaloAlimentacion;
    fields.subsidizedDistance.value = normalizedConfig.max_subsidized_distance_frac;

    fields.commercialCost.value = aeronaves.commercial?.costoKm;
    fields.commercialTime.value = aeronaves.commercial?.tiempoKm;
    fields.regionalCost.value = aeronaves.regional?.costoKm;
    fields.regionalTime.value = aeronaves.regional?.tiempoKm;
    fields.propellerCost.value = aeronaves.propeller?.costoKm;
    fields.propellerTime.value = aeronaves.propeller?.tiempoKm;
  }

  function readForm() {
    const normalizedConfig = normalizeConfig(currentConfig ?? {});

    return {
      aeronaves: {
        commercial: {
          costoKm: readNumberField(fields.commercialCost, normalizedConfig.aeronaves.commercial.costoKm),
          tiempoKm: readNumberField(fields.commercialTime, normalizedConfig.aeronaves.commercial.tiempoKm),
        },
        regional: {
          costoKm: readNumberField(fields.regionalCost, normalizedConfig.aeronaves.regional.costoKm),
          tiempoKm: readNumberField(fields.regionalTime, normalizedConfig.aeronaves.regional.tiempoKm),
        },
        propeller: {
          costoKm: readNumberField(fields.propellerCost, normalizedConfig.aeronaves.propeller.costoKm),
          tiempoKm: readNumberField(fields.propellerTime, normalizedConfig.aeronaves.propeller.tiempoKm),
        },
      },
      presupuestoMinimoPorc: readNumberField(fields.budgetThreshold, normalizedConfig.presupuestoMinimoPorc),
      intervaloAlojamiento: readNumberField(fields.lodgingInterval, normalizedConfig.intervaloAlojamiento),
      intervaloAlimentacion: readNumberField(fields.mealInterval, normalizedConfig.intervaloAlimentacion),
      max_subsidized_distance_frac: readNumberField(fields.subsidizedDistance, normalizedConfig.max_subsidized_distance_frac),
    };
  }

  async function loadConfig() {
    // Populate the modal with the active graph configuration.
    const config = await apiGet("/api/config");
    currentConfig = normalizeConfig(config);
    fillForm(currentConfig);
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
    currentConfig = normalizeConfig(response.config ?? payload);
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

  closeModal();

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
