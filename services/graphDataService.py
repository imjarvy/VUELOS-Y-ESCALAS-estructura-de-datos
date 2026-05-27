#este es el mismo archivo que pretendia ser graph_loader.py
from typing import Any, Dict, List, Optional, Tuple

from core.graph import Graph
from models.airport import Airport
from models.route import Route
from models.planner_models import Activity, JobOffer


class GraphDataService:
    """Convert raw airport graph JSON into domain objects and graph structures."""

    def __init__(self, raw_data: Optional[Dict[str, Any]] = None):
        self.raw_data = raw_data or {}

    def _get_payload_lists(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Return the airports and routes arrays from the loaded payload."""
        if not isinstance(self.raw_data, dict):
            return [], []

        # Accept only English top-level keys: `airports` and `routes`.
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

            # Only accept English keys for the rest of the fields.
            name = airport_data.get("name") or airport_id or ""
            city = airport_data.get("city") or ""
            country = airport_data.get("country") or ""
            timezone = airport_data.get("timezone") or airport_data.get("time_zone") or airport_data.get("tz") or ""

            if not airport_id:
                # skip entries without any id
                continue

            airports.append(
                Airport(
                    airport_id=airport_id,
                    name=name,
                    city=city,
                    country=country,
                    timezone=timezone,
                    is_hub=airport_data.get("isHub") or airport_data.get("is_hub", False),
                    accommodation_cost=airport_data.get("lodgingCost") or airport_data.get("accommodation_cost", 0.0),
                    feeding_cost=airport_data.get("foodCost") or airport_data.get("feeding_cost", 0.0),
                    activities=[
                        Activity(
                            id=(a.get("id") or a.get("name") or ""),
                            name=(a.get("name") or ""),
                            type=(a.get("type") or ""),
                            duration_min=int(a.get("duration_min") or a.get("duration") or 0),
                            cost_usd=float(a.get("cost_usd") or a.get("cost") or 0.0),
                        )
                        for a in (airport_data.get("activities", []) or [])
                        if isinstance(a, dict)
                    ],
                    jobs=[
                        JobOffer(
                            id=(j.get("id") or j.get("name") or ""),
                            name=(j.get("name") or ""),
                            hourly_rate=float(j.get("hourly_rate") or 0.0),
                            max_hours=int(j.get("max_hours") or 0),
                        )
                        for j in (airport_data.get("jobs", []) or [])
                        if isinstance(j, dict)
                    ],
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

            # Accept multiple naming conventions, including *_vertex variants
            # Only English keys allowed for routes
            origin = route_data.get("origin_vertex") or route_data.get("origin") or route_data.get("from")
            target = route_data.get("destination_vertex") or route_data.get("destination") or route_data.get("to")

            distance = route_data.get("distance") or route_data.get("distanceKm") or route_data.get("distance_km")

            if not origin or not target or distance is None:
                continue

            routes.append(
                Route(
                    origin_vertex=origin,
                    destination_vertex=target,
                    distance=distance,
                    aircrafts=route_data.get("aircraft", []) or route_data.get("aircrafts", []),
                    cost=route_data.get("baseCost", 0.0) or route_data.get("cost", 0.0),
                    minimum_stay=route_data.get("minimumStay", 0) or route_data.get("minimum_stay", 0),
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

    def export_payload(self, spanish: bool = False) -> Dict[str, Any]:
        """Return a serializable payload reconstructed from parsed airports.

        If `spanish` is True the payload uses Spanish keys (legacy support).
        Default returns English keys.
        """
        airports = self.get_parsed_airports()

        def airport_to_spanish(a: Airport) -> Dict[str, Any]:
            d = a.to_dict()
            return {
                "id": d.get("airport_id"),
                "nombre": d.get("name"),
                "ciudad": d.get("city"),
                "esHub": d.get("is_hub"),
                "costoAlojamiento": d.get("accommodation_cost"),
                "costoAlimentacion": d.get("feeding_cost"),
                "actividades": d.get("activities", []),
                "trabajos": d.get("jobs", []),
            }

        if spanish:
            return {"aeropuertos": [airport_to_spanish(a) for a in airports]}

        # English-style payload (default)
        return {"airports": [a.to_dict() for a in airports]}
