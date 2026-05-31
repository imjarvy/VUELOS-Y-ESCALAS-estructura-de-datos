"""Route optimizer — Dijkstra implementation (R2).

Structure:
    _AIRCRAFT_NAME_MAP  — normalizes JSON keys ("Comercial") to
                          constants.py keys ("commercial").
    _pick_best_aircraft — for a given route, selects the aircraft that
                          minimizes the current weight criterion.
    _dijkstra           — core algorithm, adapted directly from el collab of the professor.
                          Same dist/pred/unvisited structure, same min() call.
    _build_itinerary    — converts the path + pred dict into an Itinerary
                          with proper Leg objects.
    CostOptimizer       — Dijkstra weighted by USD cost.
    TimeOptimizer       — Dijkstra weighted by flight time (min).
    DistanceOptimizer   — Dijkstra weighted by distance (km).
"""

import math
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.graph import Graph
from models.itinerary import Itinerary
from models.leg import Leg
from services.base_optimizer import BaseOptimizer
from utils.constants import AIRCRAFT_RATES



# Aircraft name normalization                                         #
# ------------------------------------------------------------------ #
# Maps JSON values → constants.py keys.
# Ensures aircraft names are consistent; prevents skipped routes.

_AIRCRAFT_NAME_MAP: Dict[str, str] = {
    "Comercial": "commercial",
    "Regional":  "regional",
    "Helice":    "propeller",
    "Hélice":    "propeller",
    "comercial": "commercial",
    "regional":  "regional",
    "helice":    "propeller",
    "hélice":    "propeller",
    "commercial": "commercial",
    "Commercial": "commercial",  # ← Agregar mayúscula
    "regional": "regional",
    "Regional": "regional",      # ← Agregar mayúscula
    "propeller":  "propeller",
    "Propeller": "propeller",    # ← Agregar mayúscula
}



# Internal helpers                                                    #
# ------------------------------------------------------------------ #
def _pick_best_aircraft(
    route_aircrafts: List[str],
    distance: float,
    weight_fn: Callable[[float, Dict[str, float]], float],
    allowed_keys: Optional[Set[str]],
) -> Tuple[float, str, str]:
    """
    Select the aircraft that minimizes the weight function.

    Returns (weight, aircraft_name, aircraft_key).
    If none valid, returns (∞, "", "") so the edge is skipped.
    """
    best_weight, best_name, best_key = math.inf, "", ""

    for name in route_aircrafts:
        key = _AIRCRAFT_NAME_MAP.get(name)
        if key is None or (allowed_keys and key not in allowed_keys):
            continue

        rates = AIRCRAFT_RATES.get(key)
        if not rates:
            continue

        w = weight_fn(distance, rates)
        if w < best_weight:
            best_weight, best_name, best_key = w, name, key

    return best_weight, best_name, best_key


def _dijkstra(
    graph: Graph,
    origin: str,
    dest: str,
    weight_fn: Callable[[float, Dict[str, float]], float],
    allowed_keys: Optional[Set[str]],
    include_secondary: bool,
) -> Optional[Tuple[List[str], Dict[str, Tuple[Optional[str], str, str]]]]:
    """
    Dijkstra shortest path.

    - Uses dist/pred/unvisited structure.
    - Adds aircraft choice and hub filtering.
    - Returns (path, pred) or None if unreachable.
    """
    all_ids = [v.airport_id for v in graph.vertices]
    dist = {v: math.inf for v in all_ids}
    dist[origin] = 0.0
    pred = {v: (None, "", "") for v in all_ids}
    unvisited = set(all_ids)

    while unvisited:
        u = min(unvisited, key=lambda v: dist[v])
        if dist[u] == math.inf:
            break
        unvisited.remove(u)
        if u == dest:
            break

        for route in graph.get_neighbors(u):
            v = route.destination_vertex
            if v not in unvisited:
                continue

            if not include_secondary and v != dest:
                airport = graph.get_vertex(v)
                if airport and not airport.is_hub:
                    continue

            edge_weight, aircraft_name, aircraft_key = _pick_best_aircraft(
                route.aircrafts, route.distance, weight_fn, allowed_keys
            )
            if edge_weight == math.inf:
                continue

            new_dist = dist[u] + edge_weight
            if new_dist < dist[v]:
                dist[v] = new_dist
                pred[v] = (u, aircraft_name, aircraft_key)

    if dist[dest] == math.inf:
        return None

    path, current = [], dest
    while current is not None:
        path.insert(0, current)
        prev, _, _ = pred[current]
        current = prev

    return path, pred


def _build_itinerary(
    graph: Graph,
    path: List[str],
    pred: Dict[str, Tuple[Optional[str], str, str]],
    criteria: str,
) -> Itinerary:
    """
    Build an Itinerary from Dijkstra result.

    Each hop becomes a Leg with distance, cost, and time.
    """
    itinerary = Itinerary(optimization_criteria=criteria)

    for i in range(1, len(path)):
        current_id = path[i]
        prev_id, aircraft_name, aircraft_key = pred[current_id]

        route = next((r for r in graph.get_neighbors(prev_id)
                      if r.destination_vertex == current_id), None)
        if not route:
            continue

        rates = AIRCRAFT_RATES.get(aircraft_key, {})
        leg = Leg(
            origin_id=prev_id,
            destination_id=current_id,
            aircraft=aircraft_name,
            distance=route.distance,
            flight_time_min=round(route.distance * rates.get("time_per_km_min", 0.0), 2),
            leg_cost=round(route.distance * rates.get("cost_per_km", 0.0), 2),
        )
        itinerary.add_leg(leg)

    return itinerary


# ------------------------------------------------------------------ #
# Public optimizer classes                                            #
# ------------------------------------------------------------------ #
class CostOptimizer(BaseOptimizer):
    """Dijkstra weighted by cost (USD)."""

    @property
    def name(self) -> str:
        return "cost"

    def optimize(self, graph: Graph, origin: str, dest: str,
                 transport_types: Optional[List[str]] = None,
                 include_secondary: bool = True, **params: Any) -> Optional[Itinerary]:
        self.validate_endpoints(graph, origin, dest)
        allowed = set(transport_types) if transport_types else None
        result = _dijkstra(graph, origin, dest,
                           lambda d, r: d * r.get("cost_per_km", math.inf),
                           allowed, include_secondary)
        return None if result is None else _build_itinerary(graph, *result, criteria="cost")


class TimeOptimizer(BaseOptimizer):
    """Dijkstra weighted by flight time (minutes)."""

    @property
    def name(self) -> str:
        return "time"

    def optimize(self, graph: Graph, origin: str, dest: str,
                 transport_types: Optional[List[str]] = None,
                 include_secondary: bool = True, **params: Any) -> Optional[Itinerary]:
        self.validate_endpoints(graph, origin, dest)
        allowed = set(transport_types) if transport_types else None
        result = _dijkstra(graph, origin, dest,
                           lambda d, r: d * r.get("time_per_km_min", math.inf),
                           allowed, include_secondary)
        return None if result is None else _build_itinerary(graph, *result, criteria="time")


class DistanceOptimizer(BaseOptimizer):
    """Dijkstra weighted by distance (km)."""

    @property
    def name(self) -> str:
        return "distance"

    def optimize(self, graph: Graph, origin: str, dest: str,
                 transport_types: Optional[List[str]] = None,
                 include_secondary: bool = True, **params: Any) -> Optional[Itinerary]:
        self.validate_endpoints(graph, origin, dest)
        allowed = set(transport_types) if transport_types else None
        result = _dijkstra(graph, origin, dest,
                           lambda d, r: d, allowed, include_secondary)
        return None if result is None else _build_itinerary(graph, *result, criteria="distance")
