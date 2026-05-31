from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from core.graph import Graph
from models.itinerary import Itinerary
from models.leg import Leg
from models.trip_config import TripConfig
from services.itinerary_planner import ItineraryPlanner
from services.route_optimizer import CostOptimizer, DistanceOptimizer, TimeOptimizer


class RouteBlockingService:
    """Single-purpose service to mark routes as blocked in the in-memory graph.

    Responsibilities:
    - Find routes by origin and destination
    - Serialize routes into plain dictionaries
    - Mark routes as blocked or unblocked
    - List blocked routes for UI and persistence use
    - Recalculate planner/optimizer itineraries when a blocked edge affects them
    """

    def __init__(self) -> None:
        """Initialize the blocker with planner helpers used for recalculation."""
        self._planner = ItineraryPlanner()
        self._optimizers = {
            "cost": CostOptimizer(),
            "time": TimeOptimizer(),
            "distance": DistanceOptimizer(),
        }

    @staticmethod
    def _normalize_code(value: Any) -> str:
        """Normalize an airport code.

        Args:
            value: Raw code value.

        Returns:
            str: Uppercased, trimmed code.
        """
        return str(value or "").strip().upper()

    def _clone_graph_with_forbidden_airports(self, graph: Any, forbidden_airports: Sequence[str]) -> Any:
        """Clone a graph and block every route whose destination is forbidden.

        Args:
            graph: Source graph to duplicate.
            forbidden_airports: Airport codes that must be excluded from the
                recalculation suffix.

        Returns:
            Any: A cloned graph with the forbidden destinations marked as blocked.
        """
        if graph is None:
            return None

        cloned = Graph.from_dict(graph.to_dict())
        forbidden = {self._normalize_code(code) for code in forbidden_airports if self._normalize_code(code)}
        if not forbidden:
            return cloned

        for airport in getattr(cloned, "vertices", []) or []:
            for route in getattr(airport, "adjacencies", []) or []:
                if self._normalize_code(getattr(route, "destination_vertex", None)) in forbidden:
                    route.blocked = True

        return cloned

    @staticmethod
    def _build_itinerary(legs: Sequence[Leg], criteria: str) -> Optional[Itinerary]:
        """Build an itinerary from a leg sequence.

        Args:
            legs: Ordered list of legs to append.
            criteria: Optimization criteria label stored in the itinerary.

        Returns:
            Optional[Itinerary]: A connected itinerary, or None when there are no
            legs to reconstruct.
        """
        if not legs:
            return None

        itinerary = Itinerary(optimization_criteria=criteria)
        for leg in legs:
            itinerary.add_leg(leg)
        return itinerary

    def _find_blocked_leg_index(self, itinerary: Itinerary, origin: str, destination: str) -> Optional[int]:
        """Find the index of the leg interrupted by the blocked route.

        Args:
            itinerary: Original itinerary to inspect.
            origin: Blocked leg origin code.
            destination: Blocked leg destination code.

        Returns:
            Optional[int]: Zero-based index of the matching leg, or None when the
            blocked segment is not part of the itinerary.
        """
        origin_code = self._normalize_code(origin)
        destination_code = self._normalize_code(destination)

        for index, leg in enumerate(getattr(itinerary, "legs", []) or []):
            if self._normalize_code(getattr(leg, "origin_id", None)) == origin_code and self._normalize_code(getattr(leg, "destination_id", None)) == destination_code:
                return index
        return None

    @staticmethod
    def _remaining_resources_from_prefix(itinerary: Itinerary, prefix_end_index: int, request: Dict[str, Any]) -> Dict[str, float]:
        """Compute the remaining budget and time after the preserved prefix.

        Args:
            itinerary: Original itinerary used as the consumption baseline.
            prefix_end_index: Index where the preserved path stops.
            request: Original planner request containing budget and time fields.

        Returns:
            Dict[str, float]: Remaining budget and remaining hours for the suffix.
        """
        prefix_legs = list(getattr(itinerary, "legs", [])[:prefix_end_index])
        consumed_budget = sum(float(getattr(leg, "leg_cost", 0.0) or 0.0) for leg in prefix_legs)
        consumed_time_min = sum(float(getattr(leg, "flight_time_min", 0.0) or 0.0) for leg in prefix_legs)
        initial_budget = float(request.get("budget", request.get("budget_initial", 0.0)) or 0.0)
        initial_time_hours = float(request.get("time_hours", request.get("time_available_h", 0.0)) or 0.0)

        return {
            "budget": max(initial_budget - consumed_budget, 0.0),
            "time_hours": max(initial_time_hours - (consumed_time_min / 60.0), 0.0),
        }

    def _recalculate_suffix(
        self,
        graph: Any,
        request: Dict[str, Any],
        itinerary_data: Optional[Dict[str, Any]],
        blocked_origin: str,
        blocked_destination: str,
        planner_kind: str,
        planner_key: str,
    ) -> Optional[Dict[str, Any]]:
        """Recalculate the affected suffix from the airport where the route broke.

        Args:
            graph: Current graph instance.
            request: Original planner request used to preserve filters and limits.
            itinerary_data: Serialized itinerary to inspect and split.
            blocked_origin: Origin of the blocked route.
            blocked_destination: Destination of the blocked route.
            planner_kind: Planner family, either ``basic`` or ``route``.
            planner_key: Result key to recalculate within that family.

        Returns:
            Optional[Dict[str, Any]]: Recalculation payload with the cut airport,
            preserved prefix airports, and merged itinerary.
        """
        if not itinerary_data:
            return None

        original_itinerary = Itinerary.from_dict(itinerary_data)
        cut_index = self._find_blocked_leg_index(original_itinerary, blocked_origin, blocked_destination)
        if cut_index is None:
            return None

        prefix_legs = list(original_itinerary.legs[:cut_index])
        prefix_airports = list(original_itinerary.visited_airports[: cut_index + 1])
        cut_airport = prefix_airports[-1] if prefix_airports else self._normalize_code(blocked_origin)
        original_destination = original_itinerary.visited_airports[-1] if original_itinerary.visited_airports else ""
        destination_airport = self._normalize_code(request.get("dest") or original_destination)

        cloned_graph = self._clone_graph_with_forbidden_airports(graph, prefix_airports)
        if cloned_graph is None:
            return None

        if planner_kind == "basic":
            resources = self._remaining_resources_from_prefix(original_itinerary, cut_index, request)
            transport_types = request.get("transport_types") or None
            include_secondary = bool(request.get("include_secondary", True))
            config = TripConfig(
                budget_initial=resources["budget"],
                time_available_h=resources["time_hours"],
                preferred_aircraft=list(transport_types or []),
                allow_secondary_airports=include_secondary,
            )

            if planner_key == "itinerary_a":
                suffix = self._planner.plan_max_destinations_by_budget(cloned_graph, cut_airport, config)
                criteria = "cost"
            elif planner_key == "itinerary_b":
                suffix = self._planner.plan_max_destinations_by_time(cloned_graph, cut_airport, config)
                criteria = "time"
            else:
                return None
        else:
            optimizer = self._optimizers.get(planner_key)
            if optimizer is None or not destination_airport:
                return None

            transport_types = request.get("transport_types") or None
            include_secondary = bool(request.get("include_secondary", True))
            suffix = optimizer.optimize(
                graph=cloned_graph,
                origin=cut_airport,
                dest=destination_airport,
                transport_types=transport_types,
                include_secondary=include_secondary,
            )
            criteria = planner_key

        if suffix is None:
            return None

        merged_legs = list(prefix_legs) + list(getattr(suffix, "legs", []) or [])
        merged = self._build_itinerary(merged_legs, criteria)
        if merged is None:
            return None

        return {
            "cut_airport": cut_airport,
            "prefix_airports": prefix_airports,
            "itinerary": merged.to_dict(),
        }

    def recalculate_from_planner_context(
        self,
        graph: Any,
        planner_context: Optional[Dict[str, Any]],
        blocked_origin: str,
        blocked_destination: str,
    ) -> Optional[Dict[str, Any]]:
        """Recalculate planner output when a blocked edge affects a saved request.

        Args:
            graph: Current graph instance.
            planner_context: Context captured from the planner UI.
            blocked_origin: Origin code of the blocked route.
            blocked_destination: Destination code of the blocked route.

        Returns:
            Optional[Dict[str, Any]]: Updated planner payload, or None when the
            blocker cannot derive a valid recalculation.
        """
        if graph is None or not isinstance(planner_context, dict):
            return None

        mode = str(planner_context.get("mode") or planner_context.get("planner_mode") or "").strip().lower()
        request = dict(planner_context.get("request") or planner_context.get("lastRequest") or {})
        if not request:
            request = {
                "origin": planner_context.get("origin"),
                "dest": planner_context.get("dest"),
                "budget": planner_context.get("budget"),
                "time_hours": planner_context.get("time_hours"),
                "transport_types": planner_context.get("transport_types"),
                "include_secondary": planner_context.get("include_secondary", True),
            }

        if mode not in {"basic", "route"}:
            return None

        result: Dict[str, Any] = {
            "mode": mode,
            "request": request,
        }
        updates: Dict[str, Any] = {}

        if mode == "basic":
            itinerary_a = planner_context.get("itinerary_a")
            itinerary_b = planner_context.get("itinerary_b")
            result["itinerary_a"] = itinerary_a
            result["itinerary_b"] = itinerary_b

            recalc_a = self._recalculate_suffix(
                graph=graph,
                request=request,
                itinerary_data=itinerary_a,
                blocked_origin=blocked_origin,
                blocked_destination=blocked_destination,
                planner_kind="basic",
                planner_key="itinerary_a",
            )
            if recalc_a:
                result["itinerary_a"] = recalc_a["itinerary"]
                updates["itinerary_a"] = recalc_a

            recalc_b = self._recalculate_suffix(
                graph=graph,
                request=request,
                itinerary_data=itinerary_b,
                blocked_origin=blocked_origin,
                blocked_destination=blocked_destination,
                planner_kind="basic",
                planner_key="itinerary_b",
            )
            if recalc_b:
                result["itinerary_b"] = recalc_b["itinerary"]
                updates["itinerary_b"] = recalc_b

        else:
            routes = dict(planner_context.get("routes") or {})
            result["routes"] = routes

            for criterion, itinerary_data in routes.items():
                recalc = self._recalculate_suffix(
                    graph=graph,
                    request=request,
                    itinerary_data=itinerary_data,
                    blocked_origin=blocked_origin,
                    blocked_destination=blocked_destination,
                    planner_kind="route",
                    planner_key=str(criterion),
                )
                if recalc:
                    result["routes"][criterion] = recalc["itinerary"]
                    updates[criterion] = recalc

        if not updates:
            return None

        result["updates"] = updates
        result["recalculated"] = True
        return result

    def find_route(self, graph: Any, origin: str, destination: str) -> Optional[Any]:
        """Find a route between two airports.

        Args:
            graph: Graph instance containing airports and routes.
            origin: Origin airport code.
            destination: Destination airport code.

        Returns:
            Any: Matching route object, or None if no route is found.
        """
        if graph is None:
            return None

        origin_code = self._normalize_code(origin)
        destination_code = self._normalize_code(destination)
        if not origin_code or not destination_code:
            return None

        origin_vertex = getattr(graph, "get_vertex", lambda _airport_id: None)(origin_code)
        if origin_vertex is None:
            return None

        for route in getattr(origin_vertex, "adjacencies", []):
            if self._normalize_code(getattr(route, "destination_vertex", None)) == destination_code:
                return route

        return None

    def list_blocked_routes(self, graph: Any) -> List[Dict[str, Any]]:
        """List all blocked routes in the graph.

        Args:
            graph: Graph instance to inspect.

        Returns:
            List[Dict[str, Any]]: Blocked routes serialized as dictionaries.
        """
        if graph is None:
            return []

        blocked_routes: List[Dict[str, Any]] = []
        for airport in getattr(graph, "vertices", []) or []:
            for route in getattr(airport, "adjacencies", []) or []:
                if bool(getattr(route, "blocked", False)):
                    blocked_routes.append(self.serialize_route(route))

        return blocked_routes

    def serialize_route(self, route: Any) -> Dict[str, Any]:
        """Serialize a route into a dictionary.

        Args:
            route: Route object or route-like value.

        Returns:
            Dict[str, Any]: Plain route data with a normalized blocked flag.
        """
        if hasattr(route, "to_dict"):
            payload = dict(route.to_dict())
        else:
            payload = {
                "origin_vertex": getattr(route, "origin_vertex", None),
                "destination_vertex": getattr(route, "destination_vertex", None),
                "distance": getattr(route, "distance", None),
                "aircrafts": list(getattr(route, "aircrafts", []) or []),
                "cost": getattr(route, "cost", None),
                "minimum_stay": getattr(route, "minimum_stay", None),
                "blocked": bool(getattr(route, "blocked", False)),
            }

        payload["blocked"] = bool(payload.get("blocked", False))
        return payload

    def block_route(
        self,
        graph: Any,
        origin: str,
        destination: str,
        reason: Optional[str] = None,
        blocked: bool = True,
        planner_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Block or unblock a route in the graph.

        Args:
            graph: Graph instance containing the route.
            origin: Origin airport code.
            destination: Destination airport code.
            reason: Optional reason for the interruption.
            blocked: Flag that indicates whether the route should be blocked.

        Returns:
            Dict[str, Any]: Result payload with the operation outcome and route data when available.
        """
        route = self.find_route(graph, origin, destination)
        if route is None:
            return {
                "found": False,
                "origin": self._normalize_code(origin),
                "destination": self._normalize_code(destination),
                "blocked": bool(blocked),
                "reason": reason,
            }

        route.blocked = bool(blocked)
        route_payload = self.serialize_route(route)

        planner_result = None
        if bool(blocked):
            planner_result = self.recalculate_from_planner_context(
                graph=graph,
                planner_context=planner_context,
                blocked_origin=origin,
                blocked_destination=destination,
            )

        return {
            "found": True,
            "origin": self._normalize_code(origin),
            "destination": self._normalize_code(destination),
            "blocked": bool(route.blocked),
            "reason": reason,
            "route": route_payload,
            "planner_result": planner_result,
        }