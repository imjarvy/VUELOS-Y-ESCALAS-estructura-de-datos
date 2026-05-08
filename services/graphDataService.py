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

        # Accept English and Spanish keys for flexibility
        airports = self.raw_data.get("airports") or self.raw_data.get("aeropuertos")
        routes = self.raw_data.get("routes") or self.raw_data.get("rutas") or self.raw_data.get("routes_list")

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
            country = airport_data.get("country") or airport_data.get("pais") or ""
            timezone = airport_data.get("time_zone") or airport_data.get("zonaHoraria") or ""

            if not airport_id or not name or not city:
                continue

            airports.append(
                Airport(
                    airport_id=airport_id,
                    name=name,
                    city=city,
                    country=country,
                    timezone=timezone,
                    is_hub=airport_data.get("is_hub", False) or airport_data.get("esHub", False),
                    accommodation_cost=airport_data.get("accommodation_cost", 0.0) or airport_data.get("costoAlojamiento", 0.0),
                    feeding_cost=airport_data.get("feeding_cost", 0.0) or airport_data.get("costoAlimentacion", 0.0),
                    activities=[
                        Activity(
                            id=(a.get("id") or a.get("name") or ""),
                            name=(a.get("name") or a.get("nombre") or ""),
                            type=(a.get("type") or a.get("tipo") or ""),
                            duration_min=int(a.get("duration_min") or a.get("duracion_min") or a.get("duration") or 0),
                            cost_usd=float(a.get("cost_usd") or a.get("cost") or 0.0),
                        )
                        for a in (airport_data.get("activities", []) or airport_data.get("actividades", []) or [])
                        if isinstance(a, dict)
                    ],
                    jobs=[
                        JobOffer(
                            id=(j.get("id") or j.get("name") or ""),
                            name=(j.get("name") or j.get("nombre") or ""),
                            hourly_rate=float(j.get("hourly_rate") or j.get("tarifa_hora") or 0.0),
                            max_hours=int(j.get("max_hours") or j.get("maximo_horas") or 0),
                        )
                        for j in (airport_data.get("jobs", []) or airport_data.get("trabajos", []) or [])
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

            origin = route_data.get("origin") or route_data.get("origen") or route_data.get("from")
            target = route_data.get("target") or route_data.get("destino") or route_data.get("to")
            distance = route_data.get("distance") or route_data.get("distanciaKm")

            if not origin or not target or distance is None:
                continue

            routes.append(
                Route(
                    origin_vertex=origin,
                    destination_vertex=target,
                    distance=distance,
                    aircrafts=route_data.get("aircrafts", []) or route_data.get("aeronaves", []),
                    cost=route_data.get("cost", 0.0) or route_data.get("costoBase", 0.0),
                    minimum_stay=route_data.get("minimum_stay", 0) or route_data.get("estaciaMinima", 0),
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

    def export_payload(self, spanish: bool = True) -> Dict[str, Any]:
        """Return a serializable payload reconstructed from parsed airports.

        If `spanish` is True the payload uses Spanish keys similar to the
        original `data.json` (e.g. `aeropuertos`, `actividades`, `trabajos`,
        `costoAlojamiento`). Otherwise it uses English keys.
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

        # English-style payload
        return {"airports": [a.to_dict() for a in airports]}
