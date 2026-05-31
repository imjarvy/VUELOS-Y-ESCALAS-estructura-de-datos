export function createRouteAnimationController({
  graphUi,
  flightAnimator,
  legsToEdgeList,
  timerApi = window,
} = {}) {
  if (!graphUi) throw new Error("graphUi is required.");
  if (!flightAnimator) throw new Error("flightAnimator is required.");
  if (typeof legsToEdgeList !== "function") throw new Error("legsToEdgeList is required.");

  let routeAnimationTimer = null;

  function clearRouteAnimationTimer() {
    if (routeAnimationTimer != null) {
      timerApi.clearTimeout(routeAnimationTimer);
      routeAnimationTimer = null;
    }
  }

  function normalizeRouteLegs(legs = []) {
    if (!Array.isArray(legs)) return [];

    return legs
      .map(leg => ({
        origin: String(leg?.origin_id ?? leg?.origin ?? leg?.source ?? "").trim().toUpperCase(),
        destination: String(leg?.destination_id ?? leg?.destination ?? leg?.target ?? "").trim().toUpperCase(),
      }))
      .filter(leg => leg.origin && leg.destination);
  }

  function stop({ clearHighlight = true } = {}) {
    clearRouteAnimationTimer();
    flightAnimator.stop();

    if (clearHighlight) {
      graphUi.clearRouteHighlight();
    }
  }

  function handleBlockedRoute(origin, destination) {
    if (!flightAnimator.isAnimatingRoute(origin, destination) && !flightAnimator.isAnimatingRoute(destination, origin)) {
      return false;
    }

    clearRouteAnimationTimer();
    graphUi.clearRouteHighlight();
    flightAnimator.blockCurrentRoute();
    return true;
  }

  function playHighlightedRoute(legs = [], { suppressFinishCallback = true } = {}) {
    clearRouteAnimationTimer();
    flightAnimator.stop();

    const edgeList = legsToEdgeList(legs);
    if (!edgeList.length) {
      graphUi.clearRouteHighlight();
      return false;
    }

    graphUi.highlightRoute(edgeList);

    const normalizedLegs = normalizeRouteLegs(legs);
    if (!normalizedLegs.length) {
      return true;
    }

    let legIndex = 0;
    const playNextLeg = () => {
      const leg = normalizedLegs[legIndex];
      if (!leg) return;

      flightAnimator.animateRoute({
        originId: leg.origin,
        destinationId: leg.destination,
        blocked: false,
        suppressFinishCallback,
      });

      legIndex += 1;
      if (legIndex < normalizedLegs.length) {
        routeAnimationTimer = timerApi.setTimeout(playNextLeg, flightAnimator.routeDurationMs);
      }
    };

    playNextLeg();
    return true;
  }

  function getCurrentRoute() {
    return flightAnimator.getCurrentRoute?.() ?? null;
  }

  return {
    playHighlightedRoute,
    clearRouteAnimationTimer,
    stop,
    handleBlockedRoute,
    getCurrentRoute,
  };
}