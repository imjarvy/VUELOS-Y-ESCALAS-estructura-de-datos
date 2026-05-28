export class FlightAnimator {
  constructor({ svgId, viewportSelector = ".graph-viewport", linkSelector = ".graph-links .link", planeRadius = 6 } = {}) {
    this.svgId = svgId;
    this.viewportSelector = viewportSelector;
    this.linkSelector = linkSelector;
    this.planeRadius = planeRadius;
    this._animationFrame = null;
    this._plane = null;
    this._activeViewport = null;
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

  animateRoute({ originId, destinationId, blocked = false, durationMs = 1400 } = {}) {
    const found = this._findLink(originId, destinationId);
    if (!found?.data) return false;

    const viewport = this._getViewport();
    if (!viewport) return false;

    const plane = this._ensurePlane(viewport);
    const linkData = found.data;

    const source = blocked ? linkData.target : linkData.source;
    const target = blocked ? linkData.source : linkData.target;
    const startX = Number(source?.x ?? 0);
    const startY = Number(source?.y ?? 0);
    const endX = Number(target?.x ?? 0);
    const endY = Number(target?.y ?? 0);

    this._setPlanePosition(plane, startX, startY);

    const startTime = performance.now();
    const step = now => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / Math.max(durationMs, 1));
      const x = startX + (endX - startX) * progress;
      const y = startY + (endY - startY) * progress;
      this._setPlanePosition(plane, x, y);

      if (progress < 1) {
        this._animationFrame = requestAnimationFrame(step);
        return;
      }

      this._animationFrame = null;
    };

    this._animationFrame = requestAnimationFrame(step);
    return true;
  }
}