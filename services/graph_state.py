from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.graph import Graph

_current_graph: Optional["Graph"] = None


def set_graph(graph: "Graph") -> None:
    """Store the graph built from the last JSON upload."""
    global _current_graph
    _current_graph = graph


def get_graph() -> Optional["Graph"]:
    return _current_graph



"""
The idea is that we just use 1 object(graph).
Singleton that holds the graph built after a JSON upload.
Shared between graph_routes.py (writer) and planner_routes.py (reader).

"""