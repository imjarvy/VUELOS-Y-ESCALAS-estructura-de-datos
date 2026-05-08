"""Flask routes for loading and exporting airport graph data."""

from flask import Blueprint, jsonify, request
from acceso_datos.dataLoader import DataLoader
from acceso_datos.graphDataService import GraphDataService

graph_bp = Blueprint("graph", __name__)

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

    graph_payload = {
        "vertices": [airport.to_dict() for airport in graph.vertices],
    }

    return jsonify(
        {
            "message": "Grafo cargado correctamente",
            "graph": graph_payload,
            "airports": len(graph.vertices),
        }
    )