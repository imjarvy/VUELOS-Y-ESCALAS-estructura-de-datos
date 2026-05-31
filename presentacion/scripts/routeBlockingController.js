export function createRouteBlockingController({
  apiPost,
  graphUi,
  flightAnimator,
  infoPanel,
  tripSessionPanel,
  setStatusMessage,
} = {}) {
  const blockedRouteCache = new Map();
  let currentGraphData = null;

  function normalizeAirportCode(value) {
    return String(value ?? "").trim().toUpperCase();
  }

  function blockedRouteKey(origin, destination) {
    const normalizedOrigin = normalizeAirportCode(origin);
    const normalizedDestination = normalizeAirportCode(destination);
    if (!normalizedOrigin || !normalizedDestination) return null;
    return `${normalizedOrigin}::${normalizedDestination}`;
  }

  function getBlockedRoutes() {
    return [...blockedRouteCache.values()];
  }

  function syncBlockedRoutes(blockedRoutes = []) {
    blockedRouteCache.clear();
    for (const route of blockedRoutes) {
      const key = blockedRouteKey(route?.origin_vertex ?? route?.origin, route?.destination_vertex ?? route?.destination);
      if (!key) continue;
      blockedRouteCache.set(key, {
        origin: normalizeAirportCode(route?.origin_vertex ?? route?.origin),
        destination: normalizeAirportCode(route?.destination_vertex ?? route?.destination),
      });
    }
    tripSessionPanel.setBlockedRoutes(getBlockedRoutes());
  }

  function clearBlockedRoutes() {
    blockedRouteCache.clear();
    tripSessionPanel.setBlockedRoutes([]);
  }

  function isRouteBlocked(origin, destination) {
    const key = blockedRouteKey(origin, destination);
    return key ? blockedRouteCache.has(key) : false;
  }

  function applyBlockedRouteVisual(origin, destination, blocked) {
    // Keep the SVG state aligned with the server-side blocked route state.
    graphUi.markLinkBlocked(origin, destination, blocked);

    if (blocked) {
      if (
        flightAnimator.isAnimatingRoute(origin, destination)
        || flightAnimator.isAnimatingRoute(destination, origin)
      ) {
        flightAnimator.blockCurrentRoute();
      }
    } else {
      flightAnimator.stop();
    }
  }

  async function interruptRoute(origin, destination, blocked = true, reason = "adverse-situation") {
    const response = await apiPost("/api/interrupt-route", {
      origin,
      destination,
      blocked,
      reason,
    });

    if (Array.isArray(response?.blocked_routes)) {
      syncBlockedRoutes(response.blocked_routes);
    }

    applyBlockedRouteVisual(origin, destination, Boolean(response?.blocked ?? blocked));

    return response;
  }

  function setGraphData(graphData) {
    currentGraphData = graphData;
    const blockedRoutes = Array.isArray(graphData?.links)
      ? graphData.links.filter(link => Boolean(link?.blocked)).map(link => ({
        origin_vertex: link?.source ?? link?.origin_vertex ?? link?.origin ?? null,
        destination_vertex: link?.target ?? link?.destination_vertex ?? link?.destination ?? null,
      }))
      : [];
    syncBlockedRoutes(blockedRoutes);
  }

  infoPanel.onAdverseSituationSelect(async (airportCode, situation) => {
    if (!currentGraphData || !Array.isArray(currentGraphData.nodes)) {
      setStatusMessage("No hay grafo cargado.", "error");
      return;
    }

    try {
      const selectedAirport = normalizeAirportCode(airportCode);
      const activeRoute = flightAnimator.getCurrentRoute();

      if (!activeRoute) {
        setStatusMessage("No hay un avión en ruta activa para cancelar.", "info");
        return;
      }

      let routeOrigin = null;
      let routeDestination = null;

      if (selectedAirport === activeRoute.origin) {
        routeOrigin = activeRoute.origin;
        routeDestination = activeRoute.destination;
      } else if (selectedAirport === activeRoute.destination) {
        routeOrigin = activeRoute.destination;
        routeDestination = activeRoute.origin;
      } else {
        setStatusMessage(
          `La cancelación aplica solo a la ruta activa (${activeRoute.origin} → ${activeRoute.destination}).`,
          "info"
        );
        return;
      }

      if (isRouteBlocked(routeOrigin, routeDestination)) {
        setStatusMessage(`La ruta ${routeOrigin} → ${routeDestination} ya está bloqueada.`, "info");
        return;
      }

      setStatusMessage(`Procesando situación adversa: ${situation} en ${routeOrigin} → ${routeDestination}...`);
      const result = await interruptRoute(routeOrigin, routeDestination, true, situation);

      if (result?.found === false) {
        setStatusMessage(`No se encontró la ruta ${routeOrigin} → ${routeDestination} para bloquear.`, "error");
        return;
      }

      setStatusMessage(`Ruta ${routeOrigin} → ${routeDestination} bloqueada.`, "info");
    } catch (err) {
      setStatusMessage(`Error bloqueando rutas: ${err.message || err}`, "error");
    }
  });

  return {
    getBlockedRoutes,
    syncBlockedRoutes,
    clearBlockedRoutes,
    isRouteBlocked,
    interruptRoute,
    setGraphData,
  };
}
