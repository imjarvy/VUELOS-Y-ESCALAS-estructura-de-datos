from __future__ import annotations

from typing import Any, Dict, List, Optional


class RouteBlockingService:
    """Single-purpose service to mark routes as blocked in the in-memory graph."""

    @staticmethod
    def _normalize_code(value: Any) -> str:
        return str(value or "").strip().upper()

    def find_route(self, graph: Any, origin: str, destination: str) -> Optional[Any]:
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
        if graph is None:
            return []

        blocked_routes: List[Dict[str, Any]] = []
        for airport in getattr(graph, "vertices", []) or []:
            for route in getattr(airport, "adjacencies", []) or []:
                if bool(getattr(route, "blocked", False)):
                    blocked_routes.append(self.serialize_route(route))

        return blocked_routes

    def serialize_route(self, route: Any) -> Dict[str, Any]:
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

    def block_route(self, graph: Any, origin: str, destination: str, reason: Optional[str] = None, blocked: bool = True) -> Dict[str, Any]:
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
        return {
            "found": True,
            "origin": self._normalize_code(origin),
            "destination": self._normalize_code(destination),
            "blocked": bool(route.blocked),
            "reason": reason,
            "route": route_payload,
        }
