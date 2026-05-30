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

function collectActivities(activities = []) {
  return activities
    .filter(activity => activity && typeof activity === "object")
    .map(activity => ({
      name: activity.name ?? activity.id ?? "Actividad sin nombre",
      type: activity.type ?? "-",
      durationMin: Number(activity.duration_min ?? activity.duration ?? 0),
      costUsd: Number(activity.cost_usd ?? activity.cost ?? 0),
    }));
}

function collectJobs(jobs = []) {
  return jobs
    .filter(job => job && typeof job === "object")
    .map(job => ({
      name: job.name ?? job.id ?? "Trabajo sin nombre",
      hourlyRate: Number(job.hourly_rate ?? 0),
      maxHours: Number(job.max_hours ?? 0),
    }));
}

export function createInfoPanel({ panelId = "airportInfoPanel", rules = {} } = {}) {
  const panel = document.getElementById(panelId);

  if (!panel) {
    throw new Error(`Info panel with id ${panelId} was not found.`);
  }

  const codeEl = panel.querySelector("#infoCode");
  const nameEl = panel.querySelector("#infoName");
  const cityEl = panel.querySelector("#infoCity");
  const countryEl = panel.querySelector("#infoCountry");
  const timezoneEl = panel.querySelector("#infoTimezone");
  const lodgingCostEl = panel.querySelector("#infoLodgingCost");
  const mealRuleEl = panel.querySelector("#infoMealRule");
  const lodgingRuleEl = panel.querySelector("#infoLodgingRule");
  const airlinesEl = panel.querySelector("#infoAirlines");
  const activitiesEl = panel.querySelector("#infoActivities");
  const jobsEl = panel.querySelector("#infoJobs");
  const adverseSituationEl = panel.querySelector("#infoAdverseSituation");

  let currentAirportCode = null;
  let onAdverseSituationSelect = null;

  function formatMoney(value) {
    const amount = Number(value);
    if (!Number.isFinite(amount)) return "-";
    return `$${amount.toFixed(2)}`;
  }

  function getLodgingIntervalLabel() {
    const intervalHours = Number(rules.intervaloAlojamiento ?? 20);
    if (!Number.isFinite(intervalHours) || intervalHours <= 0) {
      return "Cada 20 horas desde el último hospedaje";
    }
    return `Cada ${intervalHours} horas desde el último hospedaje`;
  }

  function getMealIntervalLabel() {
    const intervalHours = Number(rules.intervaloAlimentacion ?? 8);
    if (!Number.isFinite(intervalHours) || intervalHours <= 0) {
      return "Cada 8 horas desde la última comida";
    }
    return `Cada ${intervalHours} horas desde la última comida`;
  }

  function setRules(nextRules = {}) {
    rules = { ...rules, ...nextRules };
    if (lodgingRuleEl) {
      lodgingRuleEl.textContent = getLodgingIntervalLabel();
    }
  }

  function show(node) {
    if (!node || typeof node !== "object") return;

    // Use logical OR to treat empty strings as missing values
    const airportCode = node.code || node.airport_code || node.iata || node.id || "-";
    currentAirportCode = airportCode !== "-" ? airportCode : null;
    const airportName = node.name || "-";
    const city = node.city || node.name || "-";
    const country = node.country || "-";
    const timezone = node.timezone || "-";
    const lodgingCost = node.accommodation_cost ?? node.lodgingCost ?? node.accommodationCost ?? node.lodging_cost ?? null;
    const routeSummaries = collectRouteSummaries(node.adjacencies ?? []);
    const activitySummaries = collectActivities(node.activities ?? []);
    const jobSummaries = collectJobs(node.jobs ?? []);

    codeEl.textContent = airportCode;
    nameEl.textContent = airportName;
    cityEl.textContent = city;
    countryEl.textContent = country;
    timezoneEl.textContent = timezone;
    if (lodgingCostEl) {
      lodgingCostEl.textContent = formatMoney(lodgingCost);
    }
    if (mealRuleEl) {
      mealRuleEl.textContent = getMealIntervalLabel();
    }
    if (lodgingRuleEl) {
      lodgingRuleEl.textContent = getLodgingIntervalLabel();
    }

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

    if (activitiesEl) {
      activitiesEl.innerHTML = "";
      if (!activitySummaries.length) {
        const li = document.createElement("li");
        li.textContent = "Sin actividades";
        activitiesEl.appendChild(li);
      } else {
        activitySummaries.forEach(activity => {
          const li = document.createElement("li");
          li.textContent = `${activity.name} · ${activity.type} · ${activity.durationMin} min · ${formatMoney(activity.costUsd)}`;
          activitiesEl.appendChild(li);
        });
      }
    }

    if (jobsEl) {
      jobsEl.innerHTML = "";
      if (!jobSummaries.length) {
        const li = document.createElement("li");
        li.textContent = "Sin trabajos";
        jobsEl.appendChild(li);
      } else {
        jobSummaries.forEach(job => {
          const li = document.createElement("li");
          li.textContent = `${job.name} · ${formatMoney(job.hourlyRate)}/h · máx. ${job.maxHours} h`;
          jobsEl.appendChild(li);
        });
      }
    }

    if (adverseSituationEl) {
      adverseSituationEl.value = "";
    }

    panel.classList.remove("hidden");
  }

  function clear() {
    currentAirportCode = null;
    codeEl.textContent = "-";
    nameEl.textContent = "-";
    cityEl.textContent = "-";
    countryEl.textContent = "-";
    timezoneEl.textContent = "-";
    if (lodgingCostEl) lodgingCostEl.textContent = "-";
    if (mealRuleEl) mealRuleEl.textContent = getMealIntervalLabel();
    if (lodgingRuleEl) lodgingRuleEl.textContent = getLodgingIntervalLabel();
    if (adverseSituationEl) adverseSituationEl.value = "";
    airlinesEl.innerHTML = "";
    if (activitiesEl) activitiesEl.innerHTML = "";
    if (jobsEl) jobsEl.innerHTML = "";
    panel.classList.add("hidden");
  }

  if (adverseSituationEl) {
    adverseSituationEl.addEventListener("change", async (e) => {
      const situationValue = e.target.value;
      if (situationValue && currentAirportCode && onAdverseSituationSelect) {
        e.target.value = "";
        await onAdverseSituationSelect(currentAirportCode, situationValue);
      }
    });
  }

  return {
    show,
    clear,
    setRules,
    onAdverseSituationSelect: (callback) => {
      onAdverseSituationSelect = callback;
    },
  };
}
