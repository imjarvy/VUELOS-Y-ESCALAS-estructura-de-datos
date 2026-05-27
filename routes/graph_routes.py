"""Flask routes for loading, exporting, and configuring airport graph data."""

from copy import deepcopy

from flask import Blueprint, jsonify, request
from acceso_datos.dataLoader import DataLoader
from services.graphDataService import GraphDataService
from utils.constants import GRAPH_CONFIG_DEFAULTS

graph_bp = Blueprint("graph", __name__)

_GRAPH_CONFIG = deepcopy(GRAPH_CONFIG_DEFAULTS)


@graph_bp.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(deepcopy(_GRAPH_CONFIG))


@graph_bp.route("/api/config", methods=["POST"])
def save_config():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Formato de configuración inválido"}), 400

    global _GRAPH_CONFIG
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

    for key in ("presupuestoMinimoPorc", "intervaloAlojamiento", "intervaloAlimentacion"):
        if key in payload:
            try:
                next_config[key] = float(payload[key])
            except (TypeError, ValueError):
                pass

    _GRAPH_CONFIG = next_config
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

    graph_payload = {"vertices": [airport.to_dict() for airport in graph.vertices]}

    return jsonify(
        {
            "message": "Grafo cargado correctamente",
            "graph": graph_payload,
            "airports": len(graph.vertices),
        }
    )