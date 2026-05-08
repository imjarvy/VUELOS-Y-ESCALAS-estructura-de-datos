from typing import Any, Dict, List, Optional, Tuple

from core.graph import Graph
from models.airport import Airport
from models.route import Route


class GraphDataService:
    """Convert raw airport graph JSON into domain objects and graph structures."""

    def __init__(self, raw_data: Optional[Dict[str, Any]] = None):
        self.raw_data = raw_data or {}

    def _get_payload_lists(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Return the airports and routes arrays from the loaded payload."""
        if not isinstance(self.raw_data, dict):
            return [], []

        airports = self.raw_data.get("airports")
        routes = self.raw_data.get("routes")

        if not isinstance(airports, list) or not isinstance(routes, list):
            return [], []

        return airports, routes

    def get_parsed_airports(self) -> List[Airport]:
        """Parse airport dictionaries into Airport objects."""
        airports_data, _ = self._get_payload_lists()
        if not airports_data:
            return []

        airports: List[Airport] = []
        for airport_data in airports_data:
            if not isinstance(airport_data, dict):
                continue

            airport_id = (
                airport_data.get("airport_id")
                or airport_data.get("id")
                or airport_data.get("code")
                or airport_data.get("iata")
            )
            name = airport_data.get("name") or airport_data.get("nombre") or ""
            city = airport_data.get("city") or airport_data.get("ciudad") or ""

            if not airport_id or not name or not city:
                continue

            airports.append(
                Airport(
                    airport_id=airport_id,
                    name=name,
                    city=city,
                    is_hub=airport_data.get("is_hub", False),
                    accommodation_cost=airport_data.get("accommodation_cost", 0.0),
                    feeding_cost=airport_data.get("feeding_cost", 0.0),
                    activities=airport_data.get("activities", []),
                    jobs=airport_data.get("jobs", []),
                )
            )

        return airports

    def get_parsed_routes(self) -> List[Route]:
        """Parse route dictionaries into Route objects."""
        _, routes_data = self._get_payload_lists()
        if not routes_data:
            return []

        routes: List[Route] = []
        for route_data in routes_data:
            if not isinstance(route_data, dict):
                continue

            origin = route_data.get("origin") or route_data.get("source") or route_data.get("from")
            target = route_data.get("target") or route_data.get("destination") or route_data.get("to")
            distance = route_data.get("distance")

            if not origin or not target or distance is None:
                continue

            routes.append(
                Route(
                    origin_vertex=origin,
                    destination_vertex=target,
                    distance=distance,
                    aircrafts=route_data.get("aircrafts", []),
                    cost=route_data.get("cost", 0.0),
                    minimum_stay=route_data.get("minimum_stay", 0),
                )
            )

        return routes

    def build_graph(self) -> Graph:
        """Build a Graph populated with Airport vertices and Route adjacencies."""
        graph = Graph()
        airports = self.get_parsed_airports()
        routes = self.get_parsed_routes()

        airport_map = {airport.airport_id: airport for airport in airports}

        for route in routes:
            origin_airport = airport_map.get(route.origin_vertex)
            if origin_airport is not None:
                origin_airport.add_adjacency(route)

        for airport in airports:
            graph.add_vertex(airport)

        return graph