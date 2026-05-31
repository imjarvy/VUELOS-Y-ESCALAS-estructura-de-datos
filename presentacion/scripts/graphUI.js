// =============================================================================
//  Graph UI Module
//  Responsibility: transform airport data and render directed graphs with D3 using polygon/coronas layout.
// =============================================================================

/**
 * Convert a Graph domain object into the structure D3 expects.
 *
 * Expected payload:
 * - Graph object: { vertices: [Airport...] }
 * - Airport id: airport.id, airport.airport_id, airport.code, airport.airport_code, airport.iata
 * - Route origin/target: route.origin_vertex, route.destination_vertex, route.origin_id, route.destination_id
 *
 * @param {Object} graph Raw graph domain object.
 * @returns {{nodes: Array<Object>, links: Array<Object>}} Graph payload.
 */
export function transformGraphToD3Data(graph = {}) {
  const nodeMap = new Map();
  const links = [];

  const vertexList = graph?.vertices ?? [];

  const getAirportId = airport => (
    airport?.id
    ?? airport?.airport_id
    ?? airport?.code
    ?? airport?.airport_code
    ?? airport?.iata
    ?? null
  );

  const getRouteTarget = route => {
    if (typeof route === "string") return route;
    return (
      route?.destination_vertex
      ?? route?.destination_id
      ?? route?.target
      ?? route?.destination_code
      ?? null
    );
  };

  const registerNode = airport => {
    const airportId = getAirportId(airport);
    if (!airportId) return null;

    const existingNode = nodeMap.get(airportId);
    const nextNode = {
      ...(existingNode ?? {}),
      ...(airport ?? {}),
      id: airportId,
    };

    if (existingNode?.inferred) {
      delete nextNode.inferred;
    }

    nodeMap.set(airportId, nextNode);

    return airportId;
  };

  vertexList.forEach(vertex => {
    const airportId = registerNode(vertex);
    if (!airportId) return;

    const routes = vertex.adjacencies ?? [];
    routes.forEach(route => {
      const target = getRouteTarget(route);
      if (!target) return;

      const source = (
        route?.origin_vertex
        ?? route?.origin_id
        ?? route?.origin
        ?? route?.source
        ?? route?.from
        ?? airportId
      );

      links.push({
        source,
        target,
        ...(typeof route === "object" ? route : {}),
      });

      if (!nodeMap.has(target)) {
        nodeMap.set(target, { id: target, inferred: true });
      }
    });
  });

  return {
    nodes: [...nodeMap.values()],
    links,
  };
}

/**
 * Create graph UI utilities for rendering and node selection.
 *
 * @param {Object} deps Dependencies.
 * @param {Object} [deps.state] Shared app state.
 * @param {Function} [deps.onNodeSelect] Callback for node click.
 * @returns {{renderGraph: Function, selectNode: Function, stop: Function}}
 */
/**
 * Calculate node positions using polygon/coronas layout algorithm.
 * All airports are placed across concentric polygon rings.
 *
 * @param {Array<Object>} nodes List of node objects.
 * @param {number} centerX Center X coordinate.
 * @param {number} centerY Center Y coordinate.
 * @returns {Array<Object>} Nodes with calculated x, y properties.
 */
function calculatePolygonLayout(nodes, centerX, centerY) {
  const hubRadius = 90;
  const polySpacing = 300;
  const nodeRadius = 20;

  const orderedNodes = [...nodes];
  const positionedNodes = [];
  let nodeIdx = 0;
  let polygonLevel = 1;

  while (nodeIdx < orderedNodes.length) {
    const polyRadius = hubRadius + polySpacing * polygonLevel;
    const numSides = 6 + polygonLevel * 2; // Hexágono (6), octágono (8), decágono (10), etc.
    const nodesPerPoly = numSides * 2; // Duplicamos para tener más nodos
    const nodesToPlace = Math.min(nodesPerPoly, orderedNodes.length - nodeIdx);

    for (let i = 0; i < nodesToPlace; i++) {
      const angle = (i / Math.max(nodesToPlace, 1)) * 2 * Math.PI;
      positionedNodes.push({
        ...orderedNodes[nodeIdx],
        x: centerX + Math.cos(angle) * polyRadius,
        y: centerY + Math.sin(angle) * polyRadius,
      });
      nodeIdx++;
    }

    polygonLevel++;
  }

  return positionedNodes;
}

export function createGraphUi({ state = {}, onNodeSelect = () => {} } = {}) {
  const d3Api = window.d3;
  if (!d3Api) {
    throw new Error("D3 is required in window.d3 before creating Graph UI.");
  }

  let selectedNodeId = state.selectedCode ?? null;
  // Internal references to rendered links/selection for runtime updates
  let _renderedLinks = [];
  let _linkSelection = null;
  let _nodeSelection = null;
  let _routeNodeIds = new Set();

  function nodeCssClass(node) {
    let cssClass = "node";
    if (node.is_critical) cssClass += " node-critical";
    if (node.is_hub) cssClass += " node-root";
    if (String(node.id) === String(selectedNodeId)) cssClass += " node-selected";
    if (_routeNodeIds.has(String(node.id ?? "").trim().toUpperCase())) cssClass += " node-on-route";
    return cssClass;
  }

  function selectNode(nodeData, nodeSelection) {
    selectedNodeId = nodeData.id;
    state.selectedCode = nodeData.id;

    if (nodeSelection) {
      nodeSelection.attr("class", d => nodeCssClass(d));
    }

    onNodeSelect(nodeData);
  }

  /**
   * Mark or unmark a rendered link as blocked (visual only).
   * originId/destinationId should match the node ids used in the graph payload.
   * Returns true if any link was updated, false otherwise.
   */
  function markLinkBlocked(originId, destinationId, blocked = true) {
    if (!Array.isArray(_renderedLinks) || !_linkSelection) return false;

    const origin = String(originId ?? "");
    const dest = String(destinationId ?? "");
    let updated = false;

    // update underlying data
    _renderedLinks.forEach(l => {
      if (String(l._originId) === origin && String(l._destinationId) === dest) {
        l.blocked = !!blocked;
        updated = true;
      }
    });

    if (!updated) return false;

    // reflect on selection
    try {
      _linkSelection
        .classed("link-blocked", d => !!d.blocked)
        .attr("marker-end", d => d.blocked ? "none" : `url(#${d._markerId ?? markerId})`);
    } catch (e) {
      // ignore errors in UI update
    }

    return updated;
  }

  function _edgeKey(originId, destinationId) {
    return `${String(originId ?? "").trim().toUpperCase()}|${String(destinationId ?? "").trim().toUpperCase()}`;
  }

  function _applyRouteHighlightStyles() {
    if (!_linkSelection) return;

    const hasHighlight = _renderedLinks.some(link => link.highlighted);
    _linkSelection
      .classed("link-route", link => !!link.highlighted)
      .classed("link-dimmed", link => hasHighlight && !link.highlighted && !link.blocked);

    if (_nodeSelection) {
      _nodeSelection.attr("class", node => nodeCssClass(node));
    }
  }

  /** Remove route highlight from all links and nodes. */
  function clearRouteHighlight() {
    if (!Array.isArray(_renderedLinks)) return;

    _renderedLinks.forEach(link => {
      link.highlighted = false;
    });
    _routeNodeIds.clear();
    _applyRouteHighlightStyles();
  }

  /**
   * Highlight a planned route on the rendered graph.
   * @param {Array<{source?: string, target?: string, origin_id?: string, destination_id?: string}>} edgeList
   * @returns {boolean} true if at least one edge was highlighted
   */
  function highlightRoute(edgeList = []) {
    if (!Array.isArray(_renderedLinks) || !_linkSelection || !Array.isArray(edgeList)) {
      return false;
    }

    clearRouteHighlight();

    const edgeSet = new Set(
      edgeList.map(edge => _edgeKey(
        edge.source ?? edge.origin ?? edge.origin_id,
        edge.target ?? edge.destination ?? edge.destination_id,
      )),
    );

    let matched = 0;
    _renderedLinks.forEach(link => {
      if (!edgeSet.has(_edgeKey(link._originId, link._destinationId))) return;
      link.highlighted = true;
      matched += 1;
      _routeNodeIds.add(String(link._originId).trim().toUpperCase());
      _routeNodeIds.add(String(link._destinationId).trim().toUpperCase());
    });

    _applyRouteHighlightStyles();
    return matched > 0;
  }

  /**
   * Render a directed graph payload into an SVG container using polygon/coronas layout.
   *
   * @param {{nodes: Array<Object>, links: Array<Object>}|null} graphData Graph payload.
   * @param {string} svgId Target SVG element id.
   * @param {string} containerId Parent container id used for sizing.
   * @returns {void}
   */
  function renderGraph(graphData, svgId, containerId) {
    const svg = d3Api.select(`#${svgId}`);
    svg.selectAll("*").remove();

    const nodesInput = Array.isArray(graphData?.nodes) ? graphData.nodes : [];
    const linksInput = Array.isArray(graphData?.links) ? graphData.links : [];

    if (!nodesInput.length) return;

    const container = document.getElementById(containerId);
    const width = container?.clientWidth || 900;
    const height = container?.clientHeight || 550;

    svg.attr("width", width).attr("height", height);

    // Calculate polygon/coronas layout
    const layoutNodes = calculatePolygonLayout(nodesInput, width / 2, height / 2);

    const viewport = svg.append("g").attr("class", "graph-viewport");

    svg.call(
      d3Api
        .zoom()
        .scaleExtent([0.2, 4])
        .on("zoom", event => {
          viewport.attr("transform", event.transform);
        })
    );

    const markerId = `${svgId}-arrowhead`;
    const defs = svg.append("defs");

    defs
      .append("marker")
      .attr("id", markerId)
      .attr("viewBox", "0 -5 10 10")
      // Keep the arrow tip outside the target node radius (r=22).
      .attr("refX", 34)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("class", "graph-arrowhead")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "context-stroke");

    const nodes = layoutNodes.map(node => ({ ...node }));
    const nodeById = new Map(nodes.map(node => [String(node.id), node]));
    const links = linksInput.map(link => ({ ...link }));

    // Update links to reference node objects
    const renderedLinks = links.map(link => {
      // derive stable origin/destination ids from available fields
      const originId = String(link.origin_vertex ?? link.origin ?? link.source ?? "") ;
      const destinationId = String(link.destination_vertex ?? link.destination ?? link.target ?? "");
      const sourceNode = nodeById.get(originId);
      const targetNode = nodeById.get(destinationId);

      return {
        ...link,
        _originId: originId,
        _destinationId: destinationId,
        _markerId: markerId,
        source: sourceNode ?? link.source,
        target: targetNode ?? link.target,
      };
    });

    const linkSelection = viewport
      .append("g")
      .attr("class", "graph-links")
      .selectAll("line")
      .data(renderedLinks)
      .join("line")
      .attr("class", "link")
      .attr("marker-end", d => d.blocked ? "none" : `url(#${markerId})`);

    // Store selection and rendered links for runtime updates
    _linkSelection = linkSelection;
    _renderedLinks = renderedLinks;
    _routeNodeIds.clear();

    // Apply blocked styling when route contains a `blocked` truthy flag
    try {
      _linkSelection.classed("link-blocked", d => !!d.blocked);
    } catch (e) {
      // noop
    }

    const nodeSelection = viewport
      .append("g")
      .attr("class", "graph-nodes")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("class", d => nodeCssClass(d))
      .style("cursor", "pointer")
      .on("click", (_, d) => selectNode(d, nodeSelection));

    nodeSelection.append("circle").attr("r", 22);

    _nodeSelection = nodeSelection;

    nodeSelection
      .append("text")
      .attr("class", "node-code")
      .attr("dy", "0.35em")
      .text(d => d.code ?? d.airport_code ?? d.iata ?? d.id);

    nodeSelection
      .append("title")
      .text(d => {
        const name = d.name ?? d.city ?? "Airport";
        const code = d.code ?? d.airport_code ?? d.iata ?? d.id;
        return `${code}\n${name}`;
      });

    linkSelection
      .attr("x1", d => d.source?.x ?? 0)
      .attr("y1", d => d.source?.y ?? 0)
      .attr("x2", d => d.target?.x ?? 0)
      .attr("y2", d => d.target?.y ?? 0);

    // Add labels to show link distances (if present on the route object)
    const labelSelection = viewport
      .append("g")
      .attr("class", "graph-link-labels")
      .selectAll("text")
      .data(renderedLinks)
      .join("text")
      .attr("class", "link-label")
      .attr("text-anchor", "middle")
      .style("pointer-events", "none")
      .text(d => {
        const dist = d.distance ?? d.distance_km ?? d.distanceKm ?? d.distancia ?? null;
        return dist != null ? `${Math.round(dist)} km` : "";
      })
      .attr("dy", "-6")
      .attr("transform", d => {
        const sx = d.source?.x ?? 0;
        const sy = d.source?.y ?? 0;
        const tx = d.target?.x ?? 0;
        const ty = d.target?.y ?? 0;
        const mx = (sx + tx) / 2;
        const my = (sy + ty) / 2;
        const dx = tx - sx;
        const dy = ty - sy;
        let angle = (Math.atan2(dy, dx) * 180) / Math.PI;
        // Keep text readable: flip if upside-down
        if (angle > 90 || angle < -90) angle += 180;
        return `translate(${mx},${my}) rotate(${angle})`;
      });

    nodeSelection.attr("transform", d => `translate(${d.x ?? 0},${d.y ?? 0})`);
  }

  return {
    renderGraph,
    selectNode,
    stop: () => {},
    markLinkBlocked,
    highlightRoute,
    clearRouteHighlight,
  };
}
