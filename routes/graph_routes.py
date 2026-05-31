"""Flask routes for loading, exporting, and configuring airport graph data."""

from copy import deepcopy
import dataclasses

from services import graph_state, session_state
from flask import Blueprint, jsonify, request
from acceso_datos.dataLoader import DataLoader
from acceso_datos.graph_state_storage import GraphStateStorage
from services.graphDataService import GraphDataService
from services.advanced_planner import AdvancedPlanner
from services.route_blocking_service import RouteBlockingService
from utils.constants import GRAPH_CONFIG_DEFAULTS

graph_bp = Blueprint("graph", __name__)

_GRAPH_CONFIG = deepcopy(GRAPH_CONFIG_DEFAULTS)

# In-memory runtime holders for the last loaded graph and active sessions.
_LAST_GRAPH = None
_ADVANCED_PLANNER: AdvancedPlanner | None = None
_SESSIONS = {}
_ROUTE_BLOCKING_SERVICE = RouteBlockingService()
_GRAPH_STORAGE = GraphStateStorage()


def _session_has_active_route(session: object) -> bool:
    """Check whether a session already has an active route.

    Args:
        session: Session-like object to inspect.

    Returns:
        bool: True when the session contains a planned route, itinerary, or last suggestion.
    """
    state = getattr(session, "state", None)
    if state is None:
        return False

    planned_route = list(getattr(state, "planned_route", []) or [])
    itinerary = list(getattr(state, "itinerary", []) or [])
    last_suggested_route = getattr(state, "last_suggested_route", None)
    return bool(planned_route or itinerary or last_suggested_route)


def _config_lock_state() -> dict:
    """Build the current configuration lock state.

    Returns:
        dict: Lock status, active session count, active route count, and message.
    """
    active_sessions = len(_SESSIONS)
    active_routes = sum(1 for session in _SESSIONS.values() if _session_has_active_route(session))

    if active_sessions == 0:
        message = "La configuración está disponible."
    elif active_routes:
        message = "No puedes cambiar la configuración mientras haya una ruta activa o una sesión en curso."
    else:
        message = "No puedes cambiar la configuración mientras haya una sesión activa."

    return {
        "locked": bool(active_sessions),
        "active_session_count": active_sessions,
        "active_route_count": active_routes,
        "message": message,
    }


def _serialize(obj):
    """Serialize nested dataclasses and route objects into JSON-friendly values.

    Args:
        obj: Any object to serialize.

    Returns:
        Any: JSON-friendly representation of the input.
    """
    try:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return _serialize(dataclasses.asdict(obj))
    except Exception:
        pass
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        try:
            return _serialize(to_dict())
        except Exception:
            pass
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(x) for x in obj]
    return obj


def _graph_payload(graph: object) -> dict:
    """Build the API payload for the currently loaded graph.

    Args:
        graph: Graph-like object to serialize.

    Returns:
        dict: Payload with serialized vertices and airport count.
    """
    vertices = getattr(graph, "vertices", None) or []
    return {
        "vertices": [airport.to_dict() for airport in vertices],
        "airports": len(vertices),
    }


def _restore_saved_graph() -> None:
    """Restore the last saved graph into memory when available.

    Returns:
        None: This function only updates module-level state.
    """
    global _LAST_GRAPH, _ADVANCED_PLANNER
    restored_graph = _GRAPH_STORAGE.load_graph()
    if restored_graph is None:
        return
    graph_state.set_graph(restored_graph)
    _LAST_GRAPH = restored_graph
    _ADVANCED_PLANNER = AdvancedPlanner(restored_graph, defaults=_GRAPH_CONFIG)


_restore_saved_graph()


@graph_bp.route("/api/config", methods=["GET"])
def get_config():
    """Return the current graph configuration.

    Returns:
        Response: JSON response with the active configuration.
    """
    return jsonify(deepcopy(_GRAPH_CONFIG))


@graph_bp.route("/api/config/status", methods=["GET"])
def get_config_status():
    """Return the current configuration lock status.

    Returns:
        Response: JSON response with the lock state.
    """
    return jsonify(_config_lock_state())


@graph_bp.route("/api/current-graph", methods=["GET"])
def current_graph():
    """Return the last loaded graph if one is available.

    Returns:
        Response: JSON response with the loaded graph payload or a null graph.
    """
    if _LAST_GRAPH is None:
        return jsonify({"graph": None, "loaded": False}), 200

    return jsonify({"graph": _graph_payload(_LAST_GRAPH), "loaded": True})


@graph_bp.route("/api/config", methods=["POST"])
def save_config():
    """Update the graph configuration.

    Returns:
        Response: JSON response with the updated configuration or an error payload.
    """
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Formato de configuración inválido"}), 400

    lock_state = _config_lock_state()
    if lock_state["locked"]:
        return jsonify({"error": lock_state["message"], "lock_state": lock_state}), 409

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
                value = payload[key]
                if value is not None:
                    next_config[key] = float(value)
            except (TypeError, ValueError):
                pass

    _GRAPH_CONFIG = next_config
    if _ADVANCED_PLANNER is not None:
        _ADVANCED_PLANNER.defaults = deepcopy(_GRAPH_CONFIG)

    return jsonify({"message": "Configuración guardada correctamente", "config": deepcopy(_GRAPH_CONFIG)})


@graph_bp.route("/api/load-graph", methods=["POST"])
def load_graph():
    """Load a JSON file and build the graph domain objects.

    Returns:
        Response: JSON response with the loaded graph payload or an error payload.
    """
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
    _GRAPH_STORAGE.save_graph(graph)

    return jsonify(
        {
            "message": "Grafo cargado correctamente",
            "graph": _graph_payload(graph),
        }
    )


@graph_bp.route("/api/interrupt-route", methods=["POST"])
def interrupt_route():
    """Mark a route as blocked or unblocked in the loaded graph.

    Returns:
        Response: JSON response with the interruption result or an error payload.
    """
    payload = request.get_json(silent=True) or {}
    origin = payload.get("origin") or payload.get("origin_vertex")
    destination = payload.get("destination") or payload.get("destination_vertex")
    reason = payload.get("reason")
    blocked = bool(payload.get("blocked", True))

    if not origin or not destination:
        return jsonify({"error": "origin and destination are required"}), 400

    global _LAST_GRAPH
    planner_context = payload.get("planner_context")
    result = _ROUTE_BLOCKING_SERVICE.block_route(
        _LAST_GRAPH,
        origin,
        destination,
        reason=reason,
        blocked=blocked,
        planner_context=planner_context,
    )
    if not result.get("found"):
        return jsonify({"error": f"No route from {origin} to {destination}"}), 404

    _GRAPH_STORAGE.save_graph(_LAST_GRAPH)

    return jsonify({
        "message": "Route interruption updated",
        **result,
        "blocked_routes": _ROUTE_BLOCKING_SERVICE.list_blocked_routes(_LAST_GRAPH),
    }), 200
