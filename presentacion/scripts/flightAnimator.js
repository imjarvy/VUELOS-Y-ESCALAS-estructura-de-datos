export class FlightAnimator {
  constructor({
    svgId,
    viewportSelector = ".graph-viewport",
    linkSelector = ".graph-links .link",
    planeRadius = 6,
    routeDurationMs = 7000,
  } = {}) {
    this.svgId = svgId;
    this.viewportSelector = viewportSelector;
    this.linkSelector = linkSelector;
    this.planeRadius = planeRadius;
    this.routeDurationMs = Math.max(1, Number(routeDurationMs) || 7000);
    this._animationFrame = null;
    this._plane = null;
    this._activeViewport = null;
    this._currentRoute = null;
    this._isBlocked = false;
    this._startTime = null;
    this._startX = null;
    this._startY = null;
    this._endX = null;
    this._endY = null;
    this._durationMs = 0;
    this._onRouteFinished = null;
  }

  stop() {
    if (this._animationFrame != null) {
      cancelAnimationFrame(this._animationFrame);
      this._animationFrame = null;
    }

    if (this._plane) {
      this._plane.remove();
      this._plane = null;
    }

    this._currentRoute = null;
    this._isBlocked = false;
    this._startTime = null;
  }

  isAnimatingRoute(originId, destinationId) {
    if (!this._currentRoute || !this._plane || this._animationFrame == null) return false;
    const origin = String(originId ?? "").trim().toUpperCase();
    const destination = String(destinationId ?? "").trim().toUpperCase();
    return this._currentRoute.origin === origin && this._currentRoute.destination === destination;
  }

  getCurrentRoute() {
    if (!this._currentRoute || !this._plane || this._animationFrame == null) return null;
    return { ...this._currentRoute };
  }

  onRouteFinished(callback) {
    this._onRouteFinished = typeof callback === "function" ? callback : null;
  }

  blockCurrentRoute() {
    if (!this._plane || !this._currentRoute || this._isBlocked) return false;

    this._isBlocked = true;
    this._plane.setAttribute("fill", "#dc2626");
    this._plane.setAttribute("stroke", "#7f1d1d");

    // Reverse from the current in-flight position back to the origin.
    const currentX = Number(this._plane.getAttribute("cx") ?? this._startX ?? 0);
    const currentY = Number(this._plane.getAttribute("cy") ?? this._startY ?? 0);
    const originalOriginX = this._startX;
    const originalOriginY = this._startY;
    const originalTargetX = this._endX;
    const originalTargetY = this._endY;

    this._startX = currentX;
    this._startY = currentY;
    this._endX = originalOriginX;
    this._endY = originalOriginY;

    const forwardDistance = Math.hypot(originalTargetX - originalOriginX, originalTargetY - originalOriginY);
    const reverseDistance = Math.hypot(this._startX - this._endX, this._startY - this._endY);
    if (forwardDistance > 0 && Number.isFinite(forwardDistance) && Number.isFinite(reverseDistance)) {
      const speedPxPerMs = forwardDistance / Math.max(this._durationMs, 1);
      this._durationMs = Math.max(300, reverseDistance / Math.max(speedPxPerMs, 0.0001));
    }

    this._startTime = performance.now();

    return true;
  }

  _getSvg() {
    return document.getElementById(this.svgId);
  }

  _getViewport() {
    const svg = this._getSvg();
    return svg?.querySelector(this.viewportSelector) ?? null;
  }

  _findLink(originId, destinationId) {
    const svg = this._getSvg();
    if (!svg) return null;

    const origin = String(originId ?? "").trim().toUpperCase();
    const destination = String(destinationId ?? "").trim().toUpperCase();
    const links = svg.querySelectorAll(this.linkSelector);

    for (const link of links) {
      const data = link.__data__;
      const dataOrigin = String(data?._originId ?? data?.origin_vertex ?? data?.origin ?? data?.source?.id ?? "").trim().toUpperCase();
      const dataDestination = String(data?._destinationId ?? data?.destination_vertex ?? data?.destination ?? data?.target?.id ?? "").trim().toUpperCase();

      if (dataOrigin === origin && dataDestination === destination) {
        return { link, data };
      }
    }

    return null;
  }

  _ensurePlane(viewport) {
    if (this._plane && this._activeViewport === viewport) {
      return this._plane;
    }

    this.stop();

    this._activeViewport = viewport;
    this._plane = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    this._plane.setAttribute("r", String(this.planeRadius));
    this._plane.setAttribute("class", "flight-animator-plane");
    this._plane.setAttribute("fill", "#b91c1c");
    this._plane.setAttribute("stroke", "#7f1d1d");
    this._plane.setAttribute("stroke-width", "1");
    viewport.appendChild(this._plane);

    return this._plane;
  }

  _setPlanePosition(plane, x, y) {
    plane.setAttribute("cx", String(x));
    plane.setAttribute("cy", String(y));
  }

  animateRoute({ originId, destinationId, blocked = false, suppressFinishCallback = false } = {}) {
    const found = this._findLink(originId, destinationId);
    if (!found?.data) return false;

    const viewport = this._getViewport();
    if (!viewport) return false;

    const plane = this._ensurePlane(viewport);
    const linkData = found.data;

    const source = blocked ? linkData.target : linkData.source;
    const target = blocked ? linkData.source : linkData.target;
    this._startX = Number(source?.x ?? 0);
    this._startY = Number(source?.y ?? 0);
    this._endX = Number(target?.x ?? 0);
    this._endY = Number(target?.y ?? 0);
    this._durationMs = this.routeDurationMs;
    this._isBlocked = blocked;

    this._currentRoute = {
      origin: String(originId ?? "").trim().toUpperCase(),
      destination: String(destinationId ?? "").trim().toUpperCase(),
    };

    this._setPlanePosition(plane, this._startX, this._startY);

    this._startTime = performance.now();
    const step = now => {
      const elapsed = now - this._startTime;
      const progress = Math.min(1, elapsed / Math.max(this._durationMs, 1));
      const x = this._startX + (this._endX - this._startX) * progress;
      const y = this._startY + (this._endY - this._startY) * progress;
      this._setPlanePosition(plane, x, y);

      if (progress < 1) {
        this._animationFrame = requestAnimationFrame(step);
        return;
      }

      const status = this._isBlocked ? "returned" : "arrived";
      const route = this._currentRoute ? { ...this._currentRoute } : null;
      this._animationFrame = null;
      this._isBlocked = false;

      if (!suppressFinishCallback && this._onRouteFinished) {
        this._onRouteFinished({ status, route });
      }
    };

    this._animationFrame = requestAnimationFrame(step);
    return true;
  }
}