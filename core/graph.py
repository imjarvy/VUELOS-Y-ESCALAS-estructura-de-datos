from typing import Any, Dict, List, Optional, TYPE_CHECKING

from models.airport import Airport
from models.route import Route

if TYPE_CHECKING:
    from models.airport import Airport
    from models.route import Route


class Graph:
    """Represent a graph of airports and routes."""

    def __init__(self) -> None:
        """Initialize an empty graph."""
        self.vertices: List[Any] = []         
        self._vertex_map: Dict[str, Any] = {}  

    # ------------------- Vertex ------------------- #

    def add_vertex(self, vertex: Any) -> None:
        """Add an airport vertex to the graph.

        Args:
            vertex: Airport object to register in the graph.

        Returns:
            None: This method only mutates the graph.
        """
        airport_id: str = vertex.airport_id
        if airport_id in self._vertex_map:
            raise ValueError(f"Airport {airport_id!r} already exists.")
        self.vertices.append(vertex)
        self._vertex_map[airport_id] = vertex

    def get_vertex(self, airport_id: str) -> Optional[Any]:
        """Get an airport vertex by its identifier.

        Args:
            airport_id: Airport code to look up.

        Returns:
            Airport: Matching airport, or None if it does not exist.
        """
        return self._vertex_map.get(airport_id)

    # ------------------- Edge ------------------- #

    def add_edge(self, route: Any) -> None:
        """Add a route to the origin airport adjacency list.

        Args:
            route: Route object to add to the graph.

        Returns:
            None: This method only mutates the graph.
        """
        origin = self._vertex_map.get(route.origin_vertex)
        if origin is None:
            raise ValueError(f"Origin {route.origin_vertex!r} not found.")
        origin.add_adjacency(route)

    def get_neighbors(self, airport_id: str) -> List[Any]:
        """Get the outgoing routes for an airport.

        Args:
            airport_id: Airport code whose routes will be returned.

        Returns:
            List[Any]: Adjacent routes, or an empty list if the airport does not exist.
        """
        airport = self._vertex_map.get(airport_id)
        if airport is None:
            return []
        return list(airport.adjacencies)

    def remove_edge(self, origin_id: str, destination_id: str) -> bool:
        """Remove a route from the graph.

        Args:
            origin_id: Origin airport code.
            destination_id: Destination airport code.

        Returns:
            bool: True if at least one route was removed, False otherwise.
        """
        airport = self._vertex_map.get(origin_id)
        if airport is None:
            return False
        original_count = len(airport.adjacencies)
        airport.adjacencies = [
            r for r in airport.adjacencies
            if not (hasattr(r, "destination_vertex") and r.destination_vertex == destination_id)
        ]
        return len(airport.adjacencies) < original_count

    def has_edge(self, origin_id: str, destination_id: str) -> bool:
        """Check whether a route exists between two airports.

        Args:
            origin_id: Origin airport code.
            destination_id: Destination airport code.

        Returns:
            bool: True when the route exists, False otherwise.
        """
        for route in self.get_neighbors(origin_id):
            if hasattr(route, "destination_vertex") and route.destination_vertex == destination_id:
                return True
        return False

    # ------------------- Serialization ------------------- #

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the graph into a dictionary.

        Returns:
            Dict[str, Any]: Serialized graph data with nodes and links.
        """
        nodes, links = [], []
        for airport in self.vertices:
            nodes.append(airport.to_dict())
            for route in airport.adjacencies:
                route_dict = route.to_dict() if hasattr(route, "to_dict") else route
                links.append({
                    "source": route_dict.get("origin_vertex"),
                    "target": route_dict.get("destination_vertex"),
                    **route_dict,
                })
        return {"nodes": nodes, "links": links}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Graph":
        """Build a graph from a dictionary snapshot.

        Args:
            data: Serialized graph data.

        Returns:
            Graph: Reconstructed graph instance, or an empty graph if the input is invalid.
        """
        graph = cls()
        if not isinstance(data, dict):
            return graph

        vertices_data = data.get("vertices") or data.get("nodes") or data.get("airports") or []
        if not isinstance(vertices_data, list):
            vertices_data = []

        airport_map: Dict[str, Airport] = {}
        for airport_data in vertices_data:
            if not isinstance(airport_data, dict):
                continue
            airport = Airport.from_dict(airport_data)
            airport_map[airport.airport_id] = airport
            graph.add_vertex(airport)

        links_data = data.get("links") or data.get("routes") or []
        if isinstance(links_data, list) and links_data:
            has_existing_adjacencies = any(getattr(airport, "adjacencies", []) for airport in graph.vertices)
            if not has_existing_adjacencies:
                for route_data in links_data:
                    if not isinstance(route_data, dict):
                        continue
                    route = Route.from_dict(route_data)
                    origin_airport = airport_map.get(route.origin_vertex)
                    if origin_airport is not None:
                        origin_airport.add_adjacency(route)

        return graph

    # ------------------- Helpers ------------------- #

    def __len__(self) -> int:
        """Return the number of vertices in the graph.

        Returns:
            int: Vertex count.
        """
        return len(self.vertices)

    def __contains__(self, airport_id: str) -> bool:
        """Check whether an airport exists in the graph.

        Args:
            airport_id: Airport code to check.

        Returns:
            bool: True if the airport exists, False otherwise.
        """
        return airport_id in self._vertex_map

    def __repr__(self) -> str:
        """Return a compact representation of the graph.

        Returns:
            str: Human-readable graph summary.
        """
        edge_count = sum(len(v.adjacencies) for v in self.vertices)
        return f"Graph(vertices={len(self.vertices)}, edges={edge_count})"