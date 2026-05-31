"""Flask routes for loading, exporting, and configuring airport graph data."""

from copy import deepcopy
import dataclasses

from services import graph_state
from flask import Blueprint, jsonify, request
from acceso_datos.dataLoader import DataLoader
from services.graphDataService import GraphDataService
from services.advanced_planner import AdvancedPlanner
from utils.constants import GRAPH_CONFIG_DEFAULTS

graph_bp = Blueprint("graph", __name__)

_GRAPH_CONFIG = deepcopy(GRAPH_CONFIG_DEFAULTS)

# In-memory runtime holders for the last loaded graph and active sessions.
_LAST_GRAPH = None
_ADVANCED_PLANNER: AdvancedPlanner | None = None
_SESSIONS = {}


def _serialize(obj):
    try:
        if dataclasses.is_dataclass(obj):
            return _serialize(dataclasses.asdict(obj))
    except Exception:
        pass
    if hasattr(obj, "to_dict"):
        try:
            return _serialize(obj.to_dict())
        except Exception:
            pass
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(x) for x in obj]
    return obj


@graph_bp.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(deepcopy(_GRAPH_CONFIG))


@graph_bp.route("/api/config", methods=["POST"])
def save_config():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Formato de configuración inválido"}), 400

    global _GRAPH_CONFIG, _ADVANCED_PLANNER
    next_config = deepcopy(_GRAPH_CONFIG)

    aeronaves = payload.get("aeronaves")
    if isinstance(aeronaves, dict):
        next_aircrafts = dict(next_config.get("aeronaves", {}))
        for aircraft_key, aircraft_value in aeronaves.items():
            if isinstance(aircraft_value, dict):
                current = dict(next_aircrafts.get(aircraft_key, {}))
                if "costoKm" in aircraft_value:
                    current["costoKm"] = float(aircraft_value["costoKm"])
                if "tiempoKm" in aircraft_value:
                    current["tiempoKm"] = float(aircraft_value["tiempoKm"])
                next_aircrafts[aircraft_key] = current
        next_config["aeronaves"] = next_aircrafts

    for key in ("presupuestoMinimoPorc", "intervaloAlojamiento", "intervaloAlimentacion", "max_subsidized_distance_frac"):
        if key in payload:
            try:
                next_config[key] = float(payload[key])
            except (TypeError, ValueError):
                pass

    _GRAPH_CONFIG = next_config
    if _ADVANCED_PLANNER is not None:
        _ADVANCED_PLANNER.defaults = deepcopy(_GRAPH_CONFIG)

    return jsonify({"message": "Configuración guardada correctamente", "config": deepcopy(_GRAPH_CONFIG)})

@graph_bp.route("/api/load-graph", methods=["POST"])
def load_graph():
    """Load a JSON file, build the graph domain objects, and return serializable graph data."""
    file = request.files.get("file")
    if file is None:
        return jsonify({"error": "No se proporcionó archivo JSON"}), 400

    loader = DataLoader()
    success, error = loader.load_from_stream(file)
    if not success:
        return jsonify({"error": error}), 400

    service = GraphDataService(loader.get_raw_data())
    graph = service.build_graph()
    graph_state.set_graph(graph)

    # persist the last loaded graph and prepare an AdvancedPlanner for session APIs
    global _LAST_GRAPH, _ADVANCED_PLANNER
    _LAST_GRAPH = graph
    _ADVANCED_PLANNER = AdvancedPlanner(graph, defaults=_GRAPH_CONFIG)

    graph_payload = {"vertices": [airport.to_dict() for airport in graph.vertices]}

    return jsonify(
        {
            "message": "Grafo cargado correctamente",
            "graph": graph_payload,
            "airports": len(graph.vertices),
        }
    )


@graph_bp.route("/api/interrupt-route", methods=["POST"])
def interrupt_route():
    """Stub endpoint to mark a route interruption.

    Expected JSON payload:
    { "origin": "AAA", "destination": "BBB", "reason": "closure", "blocked": true }

    This endpoint only normalizes the request and returns it. The actual graph/planner
    mutation will be added later, once the second planner is ready.
    """
    payload = request.get_json(silent=True) or {}
    origin = payload.get("origin") or payload.get("origin_vertex")
    destination = payload.get("destination") or payload.get("destination_vertex")
    reason = payload.get("reason")
    blocked = bool(payload.get("blocked", True))

    if not origin or not destination:
        return jsonify({"error": "origin and destination are required"}), 400

    # TODO: integrate with GraphDataService / planner: mark route blocked, notify clients, recalculate itineraries
    return jsonify({
        "message": "Interrupt route received (stub)",
        "origin": origin,
        "destination": destination,
        "reason": reason,
        "blocked": blocked,
    }), 200


@graph_bp.route("/api/session/start", methods=["POST"])
def start_session():
    payload = request.get_json(silent=True) or {}
    origin = (payload.get("origin") or payload.get("start") or "").strip().upper()
    try:
        budget = float(payload.get("budget", 0))
    except (TypeError, ValueError):
        budget = 0.0
    try:
        time_h = float(payload.get("time_h", payload.get("hours", 72)))
    except (TypeError, ValueError):
        time_h = 72.0

    if _ADVANCED_PLANNER is None or _LAST_GRAPH is None:
        return jsonify({"error": "No graph loaded. Upload a graph first."}), 400

    try:
        session = _ADVANCED_PLANNER.start_session(origin=origin, budget=budget, time_h=time_h)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    _SESSIONS[session.session_id] = session
    proposals = session.step_proposals()
    return jsonify({
        "message": "Session started",
        "session_id": session.session_id,
        "proposals": _serialize(proposals),
        "meta": _serialize(proposals.meta),
    })


@graph_bp.route("/api/session/<session_id>/proposals", methods=["GET"])
def session_proposals(session_id: str):
    session = _SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "session not found"}), 404
    proposals = session.step_proposals()
    return jsonify({"proposals": _serialize(proposals), "meta": _serialize(proposals.meta)})


@graph_bp.route("/api/session/<session_id>/suggest-route", methods=["POST"])
def session_suggest_route(session_id: str):
    session = _SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "session not found"}), 404

    result = session.suggest_route()
    return jsonify({
        "suggested_route": _serialize(result.get("suggested_route")),
        "route_plan": _serialize(result.get("route_plan") or []),
        "proposals": _serialize(result.get("proposals")),
        "meta": _serialize(result.get("proposals").meta if result.get("proposals") is not None else {}),
    })


@graph_bp.route("/api/session/<session_id>/update-budget", methods=["POST"])
def session_update_budget(session_id: str):
    session = _SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "session not found"}), 404

    payload = request.get_json(silent=True) or {}
    try:
        budget = float(payload.get("budget"))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid budget value"}), 400

    if budget < 0:
        return jsonify({"error": "budget must be >= 0"}), 400

    # Update session state: set remaining budget, optionally raise initial budget
    session.state.budget_remaining = round(float(budget), 2)
    try:
        if float(budget) > float(getattr(session.state, "budget_initial", 0)):
            session.state.budget_initial = round(float(budget), 2)
    except Exception:
        session.state.budget_initial = round(float(budget), 2)

    proposals = session.step_proposals()
    return jsonify({
        "message": "Budget updated",
        "meta": _serialize(proposals.meta),
        "proposals": _serialize(proposals),
    })


@graph_bp.route("/api/session/<session_id>/choice", methods=["POST"])
def session_choice(session_id: str):
    session = _SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "session not found"}), 404
    payload = request.get_json(silent=True) or {}
    result = session.apply_choice(payload)
    return jsonify({
        "updated_state": _serialize(result.updated_state),
        "next_proposals": _serialize(result.next_proposals) if result.next_proposals is not None else None,
        "events": list(result.events or []),
        "errors": list(result.errors or []),
    })


@graph_bp.route("/api/session/<session_id>/report", methods=["GET"])
def session_report(session_id: str):
    session = _SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "session not found"}), 404

    report = session.finalize_and_report()
    return jsonify({
        "session_id": session_id,
        "report": _serialize(report),
    })