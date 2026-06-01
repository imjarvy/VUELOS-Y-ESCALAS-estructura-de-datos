// =============================================================================
//  Trip Session Panel
//  Responsibility: show trip budget/time summary and session proposals in the UI.
// =============================================================================

function formatMoney(value) {
  // Format numeric values as compact USD amounts for the session panel.
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "-";
  return `$${amount.toFixed(2)}`;
}

function formatMinutes(totalMinutes) {
  // Format raw minutes as a readable hours-and-minutes label.
  const minutes = Number(totalMinutes);
  if (!Number.isFinite(minutes) || minutes < 0) return "-";
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  return `${hours} h ${remaining} min`;
}

function createTag(text) {
  // Create a small pill-style label used by route and activity cards.
  const tag = document.createElement("span");
  tag.textContent = text;
  tag.className = "session-tag";
  return tag;
}

export function createTripSessionPanel({ panelId = "tripSessionPanel", rules = {} } = {}) {
  // Build the advanced planner panel, wire all controls, and expose a small API.
  const panel = document.getElementById(panelId);

  if (!panel) {
    throw new Error(`Session panel with id ${panelId} was not found.`);
  }

  const budgetInitialInput = panel.querySelector("#sessionBudgetInitial");
  const budgetRemainingEl = panel.querySelector("#sessionBudgetRemaining");
  const timeRemainingEl = panel.querySelector("#sessionTimeRemaining");
  const mealRuleEl = panel.querySelector("#sessionMealRule");
  const lodgingRuleEl = panel.querySelector("#sessionLodgingRule");

  const statusBanner = document.createElement("div");
  statusBanner.className = "session-banner";
  statusBanner.textContent = "Inicia una sesión para ver propuestas y avanzar paso a paso.";

  // Collapsed view: show a single button to activate the advanced planner
  const collapsedContainer = document.createElement("div");
  collapsedContainer.className = "session-collapsed";
  const useAdvancedBtn = document.createElement("button");
  useAdvancedBtn.id = "panelUseAdvancedPlanner";
  // Match exactly the start session button classes so the visual design is identical
  useAdvancedBtn.className = "btn btn-sm session-action-btn session-action-primary";
  useAdvancedBtn.textContent = "Usar planificador avanzado";
  collapsedContainer.appendChild(useAdvancedBtn);

  // Expanded content wrapper (holds the normal session UI)
  const contentContainer = document.createElement("div");
  contentContainer.className = "session-expanded-content";

  const collapseAdvancedBtn = document.createElement("button");
  collapseAdvancedBtn.type = "button";
  collapseAdvancedBtn.className = "btn btn-sm session-action-btn session-action-primary";
  collapseAdvancedBtn.textContent = "Cerrar planificador avanzado";

  const summaryBar = document.createElement("div");
  summaryBar.className = "session-summary-bar";
  summaryBar.innerHTML = `
    <span class="session-chip" data-chip="routes">Rutas: 0</span>
    <span class="session-chip" data-chip="activities">Actividades: 0</span>
    <span class="session-chip" data-chip="jobs">Trabajos: 0</span>
    <span class="session-chip" data-chip="mandatory">Obligatorias: 0</span>
    <span class="session-chip" data-chip="free">Tiempo libre: 0 min</span>
    <span class="session-chip" data-chip="stay">Estancia: 0 min</span>
    <span class="session-chip" data-chip="optionalStay">Opcional usado: 0 min</span>
  `;

  const summaryChips = {
    routes: summaryBar.querySelector('[data-chip="routes"]'),
    activities: summaryBar.querySelector('[data-chip="activities"]'),
    jobs: summaryBar.querySelector('[data-chip="jobs"]'),
    mandatory: summaryBar.querySelector('[data-chip="mandatory"]'),
    free: summaryBar.querySelector('[data-chip="free"]'),
    stay: summaryBar.querySelector('[data-chip="stay"]'),
    optionalStay: summaryBar.querySelector('[data-chip="optionalStay"]'),
  };

  const sessionIdRow = document.createElement("div");
  sessionIdRow.className = "info-row";
  sessionIdRow.innerHTML = '<span class="info-label">Sesión activa</span><strong id="sessionActiveId">-</strong>';
  const sessionActiveIdEl = sessionIdRow.querySelector("#sessionActiveId");

  const proposalsSection = document.createElement("div");
  proposalsSection.className = "info-block";
  proposalsSection.innerHTML = '<span class="info-label">Propuestas del paso</span>';

  const proposalsList = document.createElement("div");
  proposalsList.id = "sessionProposalsList";
  proposalsList.className = "session-proposals-list";
  proposalsSection.appendChild(proposalsList);

  const actionsRow = document.createElement("div");
  actionsRow.className = "info-row session-actions-row";

  const primaryActionsRow = document.createElement("div");
  primaryActionsRow.className = "session-actions-primary-row";

  const sessionBtn = document.createElement("button");
  sessionBtn.id = "panelStartSession";
  sessionBtn.textContent = "Iniciar sesión";
  sessionBtn.className = "btn btn-sm session-action-btn session-action-primary";

  const suggestBtn = document.createElement("button");
  suggestBtn.id = "panelSuggestRoute";
  suggestBtn.textContent = "Sugerir ruta";
  suggestBtn.className = "btn btn-sm session-action-btn session-action-primary";

  const activitiesBtn = document.createElement("button");
  activitiesBtn.id = "panelToggleActivities";
  activitiesBtn.textContent = "Ver actividades opcionales";
  activitiesBtn.className = "btn btn-sm session-action-btn session-action-primary";

  primaryActionsRow.appendChild(sessionBtn);
  primaryActionsRow.appendChild(suggestBtn);
  actionsRow.appendChild(primaryActionsRow);
  actionsRow.appendChild(activitiesBtn);

  const state = {
    budgetInitial: 1000,
    budgetRemaining: 1000,
    timeRemainingMin: 72 * 60,
    freeTimeMin: 0,
    currentStayRequiredMin: 0,
    currentOptionalStayMin: 0,
    currentAirportId: null,
    showOptionalActivities: false,
    suggestedRoute: null,
    routePlan: [],
    sessionId: null,
    proposals: null,
    graphLoaded: false,
    sessionActive: false,
    advancedVisible: false,
    blockedRoutes: [],
  };

  let _onStart = null;
  let _onSuggestRoute = null;
  let _onCancelSuggestedRoute = null;
  let _onChoice = null;
  let _onToggleSession = null;
  let _onBudgetChange = null;

  function onStart(handler) {
    // Register the handler that starts or toggles the active session.
    _onStart = handler;
  }

  function onSuggestRoute(handler) {
    // Register the handler that asks the backend for a route suggestion.
    _onSuggestRoute = handler;
  }

  function onCancelSuggestedRoute(handler) {
    // Register the handler that clears the current suggested route.
    _onCancelSuggestedRoute = handler;
  }

  function onChoice(handler) {
    // Register the handler that applies a selected activity, job, or flight.
    _onChoice = handler;
  }

  function onToggleSession(handler) {
    // Register the handler that opens or closes the advanced planner session.
    _onToggleSession = handler;
  }

  function onBudgetChange(handler) {
    // Register the handler that propagates budget updates to the backend.
    _onBudgetChange = handler;
  }

  function getMealLabel() {
    // Describe the current meal interval rule using the active configuration.
    const intervalHours = Number(rules.intervaloAlimentacion ?? 8);
    return `Cada ${Number.isFinite(intervalHours) && intervalHours > 0 ? intervalHours : 8} horas desde la última comida`;
  }

  function getLodgingLabel() {
    // Describe the current lodging interval rule using the active configuration.
    const intervalHours = Number(rules.intervaloAlojamiento ?? 20);
    return `Cada ${Number.isFinite(intervalHours) && intervalHours > 0 ? intervalHours : 20} horas desde el último hospedaje`;
  }

  function createProposalCard(title, subtitle) {
    // Create a reusable card container for routes, activities, or jobs.
    const card = document.createElement("div");
    card.className = "session-proposal-card";

    const header = document.createElement("div");
    header.className = "session-proposal-header";
    header.innerHTML = `<strong>${title}</strong><span>${subtitle}</span>`;

    const content = document.createElement("div");
    content.className = "session-proposal-content";

    card.appendChild(header);
    card.appendChild(content);
    return { card, content };
  }

  function setBanner(text, kind = "info") {
    // Update the banner state even if the banner is not shown in the panel.
    statusBanner.textContent = text;
    statusBanner.dataset.kind = kind;
  }

  function toggleOptionalActivities() {
    // Flip the optional activities visibility and rerender the panel.
    state.showOptionalActivities = !state.showOptionalActivities;
    render();
  }

  function setSuggestedRoute(nextRoute = null) {
    // Persist the current suggested route so it can survive later updates.
    state.suggestedRoute = nextRoute;
    if (!nextRoute) {
      state.routePlan = [];
    }
    render();
  }

  function setRoutePlan(nextPlan = []) {
    // Update the full route plan displayed under the suggested route.
    state.routePlan = Array.isArray(nextPlan) ? nextPlan : [];
    render();
  }

  function setBlockedRoutes(nextBlockedRoutes = []) {
    // Store the routes that should be rendered as blocked in the UI.
    state.blockedRoutes = Array.isArray(nextBlockedRoutes) ? nextBlockedRoutes.filter(Boolean) : [];
    render();
  }

  function setAdvancedVisible(nextVisible = false) {
    // Show or hide the expanded advanced planner content.
    state.advancedVisible = Boolean(nextVisible);
    render();
  }

  function isRouteBlocked(origin, destination) {
    // Check whether the requested transport route is currently blocked.
    const key = `${String(origin ?? "").trim().toUpperCase()}::${String(destination ?? "").trim().toUpperCase()}`;
    return state.blockedRoutes.some(route => {
      const blockedKey = `${String(route?.origin_vertex ?? route?.origin ?? "").trim().toUpperCase()}::${String(route?.destination_vertex ?? route?.destination ?? "").trim().toUpperCase()}`;
      return blockedKey === key;
    });
  }

  function setAvailability(nextAvailability = {}) {
    // Enable or disable controls depending on graph and session availability.
    state.graphLoaded = Boolean(nextAvailability.graphLoaded ?? state.graphLoaded);
    state.sessionActive = Boolean(nextAvailability.sessionActive ?? state.sessionActive);
    sessionBtn.disabled = !state.graphLoaded;
    suggestBtn.disabled = !state.sessionActive;
    render();
  }

  function formatRouteOption(option) {
    // Render a compact text summary for each available transport option.
    const cost = Number(option?.cost_usd ?? option?.cost ?? 0);
    const time = Number(option?.time_min ?? option?.time ?? 0);
    const subsidized = Boolean(option?.is_subsidized);
    return `${option?.aircraft ?? "-"} · ${formatMoney(cost)} · ${formatMinutes(time)}${subsidized ? " · subsidiada" : ""}`;
  }

  function renderProposals() {
    // Rebuild the proposals list using the current session state and suggestions.
    proposalsList.innerHTML = "";

    const proposals = state.proposals ?? {};
    const routes = Array.isArray(proposals.routes) ? proposals.routes : [];
    const activities = Array.isArray(proposals.activities) ? proposals.activities : [];
    const jobs = Array.isArray(proposals.jobs) ? proposals.jobs : [];
    const mandatoryActions = Array.isArray(proposals.mandatory_actions) ? proposals.mandatory_actions : [];

    if (state.suggestedRoute) {
      const suggested = document.createElement("div");
      suggested.className = "session-empty session-suggested-route";
      suggested.innerHTML = `<strong>Ruta sugerida:</strong> ${state.suggestedRoute.destination ?? "-"} · Score ${Number(state.suggestedRoute.priority_score ?? 0).toFixed(2)} · ${state.suggestedRoute.selection_reason ?? ""}`;
      proposalsList.appendChild(suggested);
    }

    if (Array.isArray(state.routePlan) && state.routePlan.length) {
      const planCard = document.createElement("div");
      planCard.className = "session-proposal-card session-route-plan";

      const planHeader = document.createElement("div");
      planHeader.className = "session-proposal-header";
      planHeader.innerHTML = '<strong>Ruta planificada</strong><span>Se mantiene hasta que completes la secuencia o cambies de plan</span>';

      const planBody = document.createElement("div");
      planBody.className = "session-proposal-content";
      const planList = document.createElement("ol");
      planList.className = "session-route-plan-list";

      state.routePlan.forEach(step => {
        const item = document.createElement("li");
        item.innerHTML = `<strong>${step.origin ?? "-"} → ${step.destination ?? "-"}</strong><span>${step.transport_option?.aircraft ?? "-"} · ${formatMoney(step.transport_option?.cost_usd ?? 0)} · ${formatMinutes(step.transport_option?.time_min ?? 0)}</span>`;
        planList.appendChild(item);
      });

      planBody.appendChild(planList);
      planCard.appendChild(planHeader);
      planCard.appendChild(planBody);
      proposalsList.appendChild(planCard);
    }

    if (!routes.length && !activities.length && !jobs.length && !mandatoryActions.length) {
      const empty = document.createElement("div");
      empty.className = "session-empty";
      empty.textContent = "Inicia una sesión y presiona «Sugerir ruta» para ver las opciones del paso.";
      proposalsList.appendChild(empty);
      return;
    }

    if (!routes.length) {
      const noRoutes = document.createElement("div");
      noRoutes.className = "session-empty session-empty-warning";
      noRoutes.textContent = "No hay rutas válidas en este paso. Revisa actividades o trabajos para seguir avanzando.";
      proposalsList.appendChild(noRoutes);
    }

    if (mandatoryActions.length) {
      const { card, content } = createProposalCard("Acciones obligatorias", "Se aplican antes de continuar");
      const list = document.createElement("ul");
      list.className = "session-inline-list";
      mandatoryActions.forEach(action => {
        const li = document.createElement("li");
        li.textContent = action;
        list.appendChild(li);
      });
      content.appendChild(list);
      proposalsList.appendChild(card);
    }

    if (routes.length) {
      const { card, content } = createProposalCard("Rutas disponibles", "Elige un vuelo para continuar");
      const routesWrap = document.createElement("div");
      routesWrap.className = "session-proposal-group";

      routes.forEach(route => {
        const routeRow = document.createElement("div");
        routeRow.className = "session-choice-row";
        const routeBlocked = Boolean(route.blocked) || isRouteBlocked(route.origin, route.destination);
        if (routeBlocked) {
          routeRow.classList.add("session-choice-blocked");
        }
        if (state.suggestedRoute?.destination === route.destination) {
          routeRow.classList.add("session-choice-suggested");
        }

        const routeMain = document.createElement("div");
        routeMain.className = "session-choice-main";
        const routeTitle = document.createElement("strong");
        routeTitle.textContent = route.destination ?? "-";
        const routeMeta = document.createElement("span");
        routeMeta.textContent = `${Number(route.distance_km ?? 0)} km · llegada estimada ${formatMinutes(route.est_arrival_min ?? 0)} · estancia mínima ${formatMinutes(route.minimum_stay_min ?? 0)}`;
        routeMain.appendChild(routeTitle);
        routeMain.appendChild(routeMeta);

        const tagRow = document.createElement("div");
        tagRow.className = "session-tag-row";
        if (state.suggestedRoute?.destination === route.destination) {
          tagRow.appendChild(createTag("Sugerida"));
        }
        if (routeBlocked) {
          const blockedTag = createTag("Bloqueada");
          blockedTag.className = "session-tag session-tag-blocked";
          tagRow.appendChild(blockedTag);
        }
        tagRow.appendChild(createTag(`${route.reachable_destinations ?? 0} destinos alcanzables`));
        tagRow.appendChild(createTag(`Score ${Number(route.priority_score ?? 0).toFixed(2)}`));
        tagRow.appendChild(createTag(`Budget ${formatMoney(route.projected_budget_after_flight ?? 0)}`));
        tagRow.appendChild(createTag(`Tiempo ${formatMinutes(route.projected_time_remaining_after_flight ?? 0)}`));
        if (route.estimated_job_income > 0) {
          tagRow.appendChild(createTag(`Trabajo potencial ${formatMoney(route.estimated_job_income)}`));
        }

        routeRow.appendChild(routeMain);
        routeRow.appendChild(tagRow);

        if (route.selection_reason) {
          const reason = document.createElement("div");
          reason.className = "session-route-reason";
          reason.textContent = route.selection_reason;
          routeRow.appendChild(reason);
        }

        const optionsWrap = document.createElement("div");
        optionsWrap.className = "session-option-list";
        const options = Array.isArray(route.transport_options) ? route.transport_options : [];
        options.forEach(option => {
          const optionRow = document.createElement("div");
          optionRow.className = "session-option-row";

          const optionText = document.createElement("span");
          optionText.textContent = formatRouteOption(option);

          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "btn btn-sm";
          btn.textContent = "Elegir vuelo";
          btn.dataset.kind = "transport";
          btn.dataset.origin = route.origin ?? state.currentAirportId ?? "";
          btn.dataset.blocked = routeBlocked ? "true" : "false";
          btn.dataset.destination = route.destination ?? "";
          btn.dataset.aircraft = option.aircraft ?? "";
          btn.disabled = routeBlocked;
          if (routeBlocked) {
            btn.title = "Esta ruta está bloqueada";
          }

          optionRow.appendChild(optionText);
          optionRow.appendChild(btn);
          optionsWrap.appendChild(optionRow);
        });

        routeRow.appendChild(optionsWrap);
        routesWrap.appendChild(routeRow);
      });

      content.appendChild(routesWrap);
      proposalsList.appendChild(card);
    }

    if (activities.length && state.showOptionalActivities) {
      const { card, content } = createProposalCard("Actividades", "Opcionales o obligatorias según la sesión");
      const activitiesWrap = document.createElement("div");
      activitiesWrap.className = "session-proposal-group";

      activities.forEach(activity => {
        const row = document.createElement("div");
        row.className = "session-choice-row";

        const main = document.createElement("div");
        main.className = "session-choice-main";
        const title = document.createElement("strong");
        title.textContent = activity.name ?? activity.id ?? "Actividad";
        const meta = document.createElement("span");
        meta.textContent = `${activity.type ?? "-"} · ${formatMinutes(activity.duration_min ?? 0)} · ${formatMoney(activity.cost_usd ?? 0)}`;
        main.appendChild(title);
        main.appendChild(meta);
        const typeTag = createTag(activity.type === "mandatory" ? "Obligatoria" : "Opcional");
        typeTag.className = `session-tag ${activity.type === "mandatory" ? "session-tag-mandatory" : "session-tag-optional"}`;

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-sm";
        btn.textContent = "Elegir actividad";
        btn.dataset.kind = "activity";
        btn.dataset.activityId = activity.id ?? activity.name ?? "";

        row.appendChild(main);
        row.appendChild(typeTag);
        row.appendChild(btn);
        activitiesWrap.appendChild(row);
      });

      content.appendChild(activitiesWrap);
      proposalsList.appendChild(card);
    } else if (activities.length && !state.showOptionalActivities) {
      const hint = document.createElement("div");
      hint.className = "session-empty";
      hint.textContent = "Hay actividades opcionales disponibles. Usa «Ver actividades opcionales» para desplegarlas.";
      proposalsList.appendChild(hint);
    }

    const budgetThreshold = Number(state.budgetInitial) * 0.35;
    const canShowJobs = Number(state.budgetRemaining) < budgetThreshold;

    if (jobs.length && canShowJobs) {
      const { card, content } = createProposalCard("Trabajos", "Disponibles si el presupuesto cae por debajo del 35%");
      const jobsWrap = document.createElement("div");
      jobsWrap.className = "session-proposal-group";

      jobs.forEach(job => {
        const row = document.createElement("div");
        row.className = "session-choice-row";

        const main = document.createElement("div");
        main.className = "session-choice-main";
        const title = document.createElement("strong");
        title.textContent = job.name ?? job.id ?? "Trabajo";
        const meta = document.createElement("span");
        meta.textContent = `${formatMoney(job.hourly_rate ?? 0)} por hora · máx. ${job.max_hours ?? 0} h`;
        main.appendChild(title);
        main.appendChild(meta);
        const jobTag = createTag("Trabajo disponible");
        jobTag.className = "session-tag session-tag-job";

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-sm";
        btn.textContent = "Elegir trabajo";
        btn.dataset.kind = "job";
        btn.dataset.jobId = job.id ?? job.name ?? "";

        row.appendChild(main);
        row.appendChild(jobTag);
        row.appendChild(btn);
        jobsWrap.appendChild(row);
      });

      content.appendChild(jobsWrap);
      proposalsList.appendChild(card);
    }
  }


  function render() {
    // Keep the DOM in sync with the panel state.
    // Ensure collapsed button and content wrapper are placed once
    if (!collapsedContainer.isConnected) panel.insertBefore(collapsedContainer, panel.firstChild);
    if (!contentContainer.isConnected) panel.appendChild(contentContainer);
    if (!collapseAdvancedBtn.isConnected) contentContainer.insertBefore(collapseAdvancedBtn, contentContainer.firstChild);

    // Move UI pieces into the content container (only once)
    // Also move any existing static rows and headings from the original markup into the content container
    const existingRows = Array.from(panel.querySelectorAll(':scope > h3, :scope > .info-row, :scope > .info-block'));
    existingRows.forEach(r => {
      if (r !== collapsedContainer && r !== contentContainer && r.parentElement !== contentContainer) {
        contentContainer.appendChild(r);
      }
    });
    if (!sessionIdRow.isConnected || sessionIdRow.parentElement !== contentContainer) contentContainer.appendChild(sessionIdRow);
    if (!summaryBar.isConnected || summaryBar.parentElement !== contentContainer) contentContainer.appendChild(summaryBar);
    if (!actionsRow.isConnected || actionsRow.parentElement !== contentContainer) contentContainer.appendChild(actionsRow);
    if (!proposalsSection.isConnected || proposalsSection.parentElement !== contentContainer) contentContainer.appendChild(proposalsSection);

    if (budgetInitialInput) budgetInitialInput.value = String(state.budgetInitial);
    if (budgetRemainingEl) budgetRemainingEl.textContent = formatMoney(state.budgetRemaining);
    if (timeRemainingEl) timeRemainingEl.textContent = formatMinutes(state.timeRemainingMin);
    if (mealRuleEl) mealRuleEl.textContent = getMealLabel();
    if (lodgingRuleEl) lodgingRuleEl.textContent = getLodgingLabel();
    if (sessionActiveIdEl) sessionActiveIdEl.textContent = state.sessionId ?? "-";

    summaryChips.routes.textContent = `Rutas: ${Array.isArray(state.proposals?.routes) ? state.proposals.routes.length : 0}`;
    summaryChips.activities.textContent = `Actividades: ${Array.isArray(state.proposals?.activities) ? state.proposals.activities.length : 0}`;
    summaryChips.jobs.textContent = `Trabajos: ${Array.isArray(state.proposals?.jobs) ? state.proposals.jobs.length : 0}`;
    summaryChips.mandatory.textContent = `Obligatorias: ${Array.isArray(state.proposals?.mandatory_actions) ? state.proposals.mandatory_actions.length : 0}`;
    summaryChips.free.textContent = `Tiempo libre: ${formatMinutes(state.freeTimeMin ?? 0)}`;
    summaryChips.stay.textContent = `Estancia: ${formatMinutes(state.currentStayRequiredMin ?? 0)}`;
    summaryChips.optionalStay.textContent = `Opcional usado: ${formatMinutes(state.currentOptionalStayMin ?? 0)}`;

    sessionBtn.disabled = !state.graphLoaded;
    suggestBtn.disabled = !state.sessionActive;
    activitiesBtn.disabled = !state.sessionActive || !(Array.isArray(state.proposals?.activities) && state.proposals.activities.length > 0);
    sessionBtn.textContent = state.sessionActive ? "Cancelar sesión" : "Iniciar sesión";
    sessionBtn.classList.toggle("session-action-primary", !state.sessionActive);
    sessionBtn.classList.toggle("session-action-danger", state.sessionActive);
    activitiesBtn.textContent = state.showOptionalActivities ? "Ocultar actividades opcionales" : "Ver actividades opcionales";
    suggestBtn.textContent = state.suggestedRoute ? "Cancelar ruta sugerida" : "Sugerir ruta";
    suggestBtn.classList.toggle("session-action-danger", Boolean(state.suggestedRoute));
    suggestBtn.classList.toggle("session-action-primary", !state.suggestedRoute);

    // Show/Hide advanced planner content
    contentContainer.style.display = state.advancedVisible ? "" : "none";
    collapsedContainer.style.display = state.advancedVisible ? "none" : "";
    useAdvancedBtn.textContent = "Usar planificador avanzado";
    collapseAdvancedBtn.style.display = state.advancedVisible ? "" : "none";

    if (!state.proposals) {
      proposalsList.innerHTML = '<div class="session-empty">Inicia una sesión y presiona «Sugerir ruta» para ver las opciones del paso.</div>';
    } else {
      renderProposals();
    }

  }

  function setRules(nextRules = {}) {
    // Refresh the panel labels and thresholds using the latest configuration.
    rules = { ...rules, ...nextRules };
    render();
  }

  function setState(nextState = {}) {
    // Merge a partial state update and rerender the panel.
    Object.assign(state, nextState);
    render();
  }

  function setSessionId(sessionId) {
    // Store the active session identifier shown in the panel header.
    state.sessionId = sessionId || null;
    render();
  }

  function setOptionalActivitiesVisible(nextVisible = false) {
    // Control whether the optional activities section is visible.
    state.showOptionalActivities = Boolean(nextVisible);
    render();
  }

  function clearProposals() {
    // Remove all current proposals from the panel.
    state.proposals = null;
    render();
  }

  function setProposals(nextProposals = null) {
    // Replace the current proposal payload and rerender the list.
    state.proposals = nextProposals;
    render();
  }

  sessionBtn.addEventListener("click", () => {
    // The main button starts or toggles the current session.
    if (typeof _onToggleSession === "function") {
      _onToggleSession();
      return;
    }
    if (typeof _onStart === "function") _onStart();
  });

  suggestBtn.addEventListener("click", () => {
    // Request or clear the suggested route from the planner.
    if (state.suggestedRoute && typeof _onCancelSuggestedRoute === "function") {
      _onCancelSuggestedRoute();
      return;
    }
    if (typeof _onSuggestRoute === "function") _onSuggestRoute();
  });

  activitiesBtn.addEventListener("click", () => {
    // Show or hide optional activities in the proposals list.
    toggleOptionalActivities();
  });

  // Toggle advanced planner visibility
  useAdvancedBtn.addEventListener("click", () => {
    // Expand the advanced planner panel from the collapsed view.
    state.advancedVisible = !state.advancedVisible;
    render();
  });

  collapseAdvancedBtn.addEventListener("click", () => {
    // Collapse the advanced planner panel back to the compact button.
    state.advancedVisible = false;
    render();
  });

  proposalsList.addEventListener("click", event => {
    // Dispatch the selected proposal back to the orchestrator.
    const button = event.target.closest("button[data-kind]");
    if (!button || typeof _onChoice !== "function") return;

    const kind = button.dataset.kind;
    const choice = { kind };

    if (kind === "transport") {
      choice.origin = button.dataset.origin || state.currentAirportId || "";
      choice.destination = button.dataset.destination || "";
      choice.aircraft = button.dataset.aircraft || "";
      choice.blocked = button.dataset.blocked === "true";
    } else if (kind === "activity") {
      choice.activity_id = button.dataset.activityId || "";
    } else if (kind === "job") {
      choice.job_id = button.dataset.jobId || "";
      const hours = prompt("Horas a trabajar:", "1");
      if (hours == null) return;
      const parsedHours = Number(hours);
      if (!Number.isFinite(parsedHours) || parsedHours <= 0) {
        alert("Ingresa un número de horas válido mayor que cero.");
        return;
      }
      choice.hours = parsedHours;
    }

    _onChoice(choice);
  });

  if (budgetInitialInput) {
    budgetInitialInput.addEventListener("change", () => {
      // Propagate budget edits to local state and to the backend if possible.
      const parsed = Number(budgetInitialInput.value);
      if (!Number.isFinite(parsed) || parsed < 0) return;
      // Update locally
      state.budgetInitial = parsed;
      if (state.budgetRemaining > parsed) {
        state.budgetRemaining = parsed;
      }
      // If a handler is registered, delegate (it may call backend to persist)
      if (typeof _onBudgetChange === "function") {
        try {
          _onBudgetChange(parsed);
        } catch (err) {
          // fallback: re-render with local change
          render();
        }
      } else {
        render();
      }
    });
  }

  render();

  return {
    setRules,
    setState,
    setSessionId,
    setProposals,
    setSuggestedRoute,
    setAvailability,
    setBanner,
    setOptionalActivitiesVisible,
    setRoutePlan,
    setBlockedRoutes,
    setAdvancedVisible,
    clearProposals,
    getState: () => ({ ...state }),
    onStart,
    onToggleSession,
    onSuggestRoute,
    onCancelSuggestedRoute,
    onBudgetChange,
    onChoice,
  };
}
