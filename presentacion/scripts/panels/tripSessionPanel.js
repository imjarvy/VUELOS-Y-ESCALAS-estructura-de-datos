// =============================================================================
//  Trip Session Panel
//  Responsibility: show trip budget/time summary in the UI.
// =============================================================================

function formatMoney(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "-";
  return `$${amount.toFixed(2)}`;
}

function formatMinutes(totalMinutes) {
  const minutes = Number(totalMinutes);
  if (!Number.isFinite(minutes) || minutes < 0) return "-";
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  return `${hours} h ${remaining} min`;
}

export function createTripSessionPanel({ panelId = "tripSessionPanel", rules = {} } = {}) {
  const panel = document.getElementById(panelId);

  if (!panel) {
    throw new Error(`Session panel with id ${panelId} was not found.`);
  }

  const budgetInitialInput = panel.querySelector("#sessionBudgetInitial");
  const budgetRemainingEl = panel.querySelector("#sessionBudgetRemaining");
  const timeRemainingEl = panel.querySelector("#sessionTimeRemaining");
  const mealRuleEl = panel.querySelector("#sessionMealRule");
  const lodgingRuleEl = panel.querySelector("#sessionLodgingRule");

  const state = {
    budgetInitial: 1000,
    budgetRemaining: 1000,
    timeRemainingMin: 72 * 60,
  };

  function getMealLabel() {
    const intervalHours = Number(rules.intervaloAlimentacion ?? 8);
    return `Cada ${Number.isFinite(intervalHours) && intervalHours > 0 ? intervalHours : 8} horas desde la última comida`;
  }

  function getLodgingLabel() {
    const intervalHours = Number(rules.intervaloAlojamiento ?? 20);
    return `Cada ${Number.isFinite(intervalHours) && intervalHours > 0 ? intervalHours : 20} horas desde el último hospedaje`;
  }

  function render() {
    if (budgetInitialInput) budgetInitialInput.value = String(state.budgetInitial);
    if (budgetRemainingEl) budgetRemainingEl.textContent = formatMoney(state.budgetRemaining);
    if (timeRemainingEl) timeRemainingEl.textContent = formatMinutes(state.timeRemainingMin);
    if (mealRuleEl) mealRuleEl.textContent = getMealLabel();
    if (lodgingRuleEl) lodgingRuleEl.textContent = getLodgingLabel();
  }

  function setRules(nextRules = {}) {
    rules = { ...rules, ...nextRules };
    render();
  }

  function setState(nextState = {}) {
    Object.assign(state, nextState);
    render();
  }

  if (budgetInitialInput) {
    budgetInitialInput.addEventListener("change", () => {
      const parsed = Number(budgetInitialInput.value);
      if (Number.isFinite(parsed) && parsed >= 0) {
        state.budgetInitial = parsed;
        if (state.budgetRemaining > parsed) {
          state.budgetRemaining = parsed;
        }
        render();
      }
    });
  }

  render();

  return {
    setRules,
    setState,
    getState: () => ({ ...state }),
  };
}