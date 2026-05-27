from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models.airport import Airport
    from models.route import Route


class Graph:
    def __init__(self) -> None:
        self.vertices: List[Any] = []          # Lista ordenada de aeropuertos
        self._vertex_map: Dict[str, Any] = {}  # airport_id → Airport (lookup O(1))

    # ------------------- Vertex ------------------- #

    def add_vertex(self, vertex: Any) -> None:
        airport_id: str = vertex.airport_id
        if airport_id in self._vertex_map:
            raise ValueError(f"Airport {airport_id!r} already exists.")
        self.vertices.append(vertex)
        self._vertex_map[airport_id] = vertex

    def get_vertex(self, airport_id: str) -> Optional[Any]:
        return self._vertex_map.get(airport_id)

    # ------------------- Edge ------------------- #

    def add_edge(self, route: Any) -> None:
        origin = self._vertex_map.get(route.origin_vertex)
        if origin is None:
            raise ValueError(f"Origin {route.origin_vertex!r} not found.")
        origin.add_adjacency(route)

    def get_neighbors(self, airport_id: str) -> List[Any]:
        airport = self._vertex_map.get(airport_id)
        if airport is None:
            return []
        return list(airport.adjacencies)

    def remove_edge(self, origin_id: str, destination_id: str) -> bool:
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
        for route in self.get_neighbors(origin_id):
            if hasattr(route, "destination_vertex") and route.destination_vertex == destination_id:
                return True
        return False

    # ------------------- Serialization ------------------- #

    def to_dict(self) -> Dict[str, Any]:
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

    # ------------------- Helpers ------------------- #

    def __len__(self) -> int:
        return len(self.vertices)

    def __contains__(self, airport_id: str) -> bool:
        return airport_id in self._vertex_map

    def __repr__(self) -> str:
        edge_count = sum(len(v.adjacencies) for v in self.vertices)
        return f"Graph(vertices={len(self.vertices)}, edges={edge_count})"