// =============================================================================
//  Graph UI Module
//  Responsibility: transform airport data and render directed graphs with D3 force.
// =============================================================================

/**
 * Convert a Graph domain object into the structure D3 force expects.
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

    if (!nodeMap.has(airportId)) {
      nodeMap.set(airportId, {
        id: airportId,
        ...airport,
      });
    }

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
export function createGraphUi({ state = {}, onNodeSelect = () => {} } = {}) {
  const d3Api = window.d3;
  if (!d3Api) {
    throw new Error("D3 is required in window.d3 before creating Graph UI.");
  }

  let simulation = null;
  let selectedNodeId = state.selectedCode ?? null;

  function nodeCssClass(node) {
    let cssClass = "node";
    if (node.is_critical) cssClass += " node-critical";
    if (node.is_hub) cssClass += " node-root";
    if (String(node.id) === String(selectedNodeId)) cssClass += " node-selected";
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

  function stop() {
    if (simulation) {
      simulation.stop();
      simulation = null;
    }
  }

  /**
   * Render a directed graph payload into an SVG container using D3 force simulation.
   *
   * @param {{nodes: Array<Object>, links: Array<Object>}|null} graphData Graph payload.
   * @param {string} svgId Target SVG element id.
   * @param {string} containerId Parent container id used for sizing.
   * @returns {void}
   */
  function renderGraph(graphData, svgId, containerId) {
    const svg = d3Api.select(`#${svgId}`);
    svg.selectAll("*").remove();

    stop();

    const nodesInput = Array.isArray(graphData?.nodes) ? graphData.nodes : [];
    const linksInput = Array.isArray(graphData?.links) ? graphData.links : [];

    if (!nodesInput.length) return;

    const container = document.getElementById(containerId);
    const width = container?.clientWidth || 900;
    const height = container?.clientHeight || 550;

    svg.attr("width", width).attr("height", height);

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
    svg
      .append("defs")
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
      .attr("fill", "#6b7280");

    const nodes = nodesInput.map(node => ({ ...node }));
    const links = linksInput.map(link => ({ ...link }));

    const linkSelection = viewport
      .append("g")
      .attr("class", "graph-links")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("class", "link")
      .attr("marker-end", `url(#${markerId})`);

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

    simulation = d3Api
      .forceSimulation(nodes)
      .force("charge", d3Api.forceManyBody().strength(-260))
      .force("center", d3Api.forceCenter(width / 2, height / 2))
      .force(
        "link",
        d3Api
          .forceLink(links)
          .id(d => d.id)
          .distance(link => link.distance ?? 130)
          .strength(link => link.strength ?? 0.35)
      )
      .force("collide", d3Api.forceCollide(30))
      .on("tick", ticked);

    function ticked() {
      linkSelection
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      nodeSelection.attr("transform", d => `translate(${d.x},${d.y})`);
    }
  }

  return {
    renderGraph,
    selectNode,
    stop,
  };
}
