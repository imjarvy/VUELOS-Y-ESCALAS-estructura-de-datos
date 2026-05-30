"""
REST endpoints  — basic itinerary planning.

Single Responsibility: this module only handles HTTP concerns:
    - parse and validate the request JSON
    - call the appropriate service
    - return a JSON response

No algorithm logic lives here. All computation is in:
    services/route_optimizer.py  (Dijkstra — best single route)
    services/itinerary_planner.py (DFS — max destinations)

Registered in app.py as:
    from routes.planner_routes import planner_bp
    app.register_blueprint(planner_bp)
"""

from flask import Blueprint, jsonify, request

from services import graph_state
from services.route_optimizer import CostOptimizer, TimeOptimizer, DistanceOptimizer
from services.itinerary_planner import ItineraryPlanner
from models.trip_config import TripConfig

planner_bp  = Blueprint("planner", __name__)
_planner    = ItineraryPlanner()
_optimizers = {
    "cost":     CostOptimizer(),
    "time":     TimeOptimizer(),
    "distance": DistanceOptimizer(),
}


def _graph_or_error():
    """Return (graph, None) if a graph is loaded, or (None, error_response)."""
    graph = graph_state.get_graph()
    if graph is None:
        return None, (
            jsonify({"error": "No hay grafo cargado. Usa POST /api/load-graph primero."}),
            400,
        )
    return graph, None


def _parse_transport_types(raw) -> list:
    """Normalize transport_types from the request body.

    Accepts None (all types allowed), a list of strings, or a single string.
    Returns an empty list when all types are allowed (planner interprets [] as None).
    """
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(t) for t in raw]
    return []



# POST /api/plan/basic                                                 
# Generates two itinerary alternatives from a single origin:          
#   A — max destinations within budget                                
#   B — max destinations within available time                        


@planner_bp.route("/api/plan/basic", methods=["POST"])
def plan_basic():
    """
    Expected JSON body:
    {
        "origin":            "BOG",
        "budget":            600.0,
        "time_hours":        50.0,
        "transport_types":   ["Comercial", "Regional"],  // [] = all allowed
        "include_secondary": true
    }

    Response:
    {
        "itinerary_a": { ...Itinerary.to_dict() },  // max destinations by budget
        "itinerary_b": { ...Itinerary.to_dict() },  // max destinations by time
        "origin":      "BOG"
    }
    """
    graph, err = _graph_or_error()
    if err:
        return err

    body = request.get_json(silent=True) or {}

    # ── Validate required fields 
    origin = body.get("origin", "").strip().upper()
    if not origin:
        return jsonify({"error": "'origin' es requerido."}), 400

    try:
        budget     = float(body.get("budget", 0))
        time_hours = float(body.get("time_hours", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "'budget' y 'time_hours' deben ser números."}), 400

    if budget <= 0:
        return jsonify({"error": "'budget' debe ser mayor a 0."}), 400
    if time_hours <= 0:
        return jsonify({"error": "'time_hours' debe ser mayor a 0."}), 400

    if origin not in graph:
        return jsonify({"error": f"Aeropuerto de origen '{origin}' no encontrado en el grafo."}), 404

    # ── Build TripConfig 
    transport_types  = _parse_transport_types(body.get("transport_types"))
    include_secondary = bool(body.get("include_secondary", True))

    config = TripConfig(
        budget_initial          = budget,
        time_available_h        = time_hours,
        preferred_aircraft      = transport_types,
        allow_secondary_airports = include_secondary,
    )

    # ── Run planner 
    try:
        itin_a, itin_b = _planner.plan_both(graph, origin, config)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "origin":      origin,
        "itinerary_a": itin_a.to_dict() if itin_a else None,
        "itinerary_b": itin_b.to_dict() if itin_b else None,
    })



# POST /api/plan/route                                                 
# Best single route between two airports by one or more criteria.     
# If multiple criteria are selected, returns one route per criterion. 

@planner_bp.route("/api/plan/route", methods=["POST"])
def plan_route():
    """
    Expected JSON body:
    {
        "origin":            "BOG",
        "dest":              "LIM",
        "criteria":          ["cost", "time", "distance"],  // one or more
        "transport_types":   ["Comercial"],                 // [] = all allowed
        "include_secondary": true
    }

    Response:
    {
        "origin": "BOG",
        "dest":   "LIM",
        "routes": {
            "cost":     { ...Itinerary.to_dict() },
            "time":     { ...Itinerary.to_dict() },
            "distance": { ...Itinerary.to_dict() }
        }
    }
    """
    graph, err = _graph_or_error()
    if err:
        return err

    body = request.get_json(silent=True) or {}

    origin = (body.get("origin") or "").strip().upper()
    dest   = (body.get("dest") or "").strip().upper()

    if not origin or not dest:
        return jsonify({"error": "'origin' y 'dest' son requeridos."}), 400

    for code, label in [(origin, "origen"), (dest, "destino")]:
        if code not in graph:
            return jsonify({"error": f"Aeropuerto de {label} '{code}' no encontrado."}), 404

    # Normalize criteria — accept string or list
    raw_criteria = body.get("criteria", list(_optimizers.keys()))
    if isinstance(raw_criteria, str):
        raw_criteria = [raw_criteria]
    criteria = [c for c in raw_criteria if c in _optimizers]

    if not criteria:
        return jsonify({
            "error": f"'criteria' debe contener al menos uno de: {list(_optimizers.keys())}"
        }), 400

    transport_types   = _parse_transport_types(body.get("transport_types"))
    include_secondary = bool(body.get("include_secondary", True))

    # ── Run one Dijkstra per selected criterion ─────────────────
    results = {}
    for criterion in criteria:
        optimizer = _optimizers[criterion]
        try:
            itin = optimizer.optimize(
                graph             = graph,
                origin            = origin,
                dest              = dest,
                transport_types   = transport_types if transport_types else None,
                include_secondary = include_secondary,
            )
            results[criterion] = itin.to_dict() if itin else None
        except ValueError as e:
            results[criterion] = {"error": str(e)}

    return jsonify({
        "origin": origin,
        "dest":   dest,
        "routes": results,
    })