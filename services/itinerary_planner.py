"""
services/itinerary_planner.py

Builds maximum-coverage itineraries under budget or time constraints (R2).

Algorithm justification:
    Allows visiting as MANY airports as possible from a single origin within a hard resource constraint (budget USD or
    time minutes). These are fundamentally different problems.

    Solution: Depth-First Search (DFS) + backtracking.
    - DFS explores all possible paths from the origin.
    - Backtracking abandons branches that exceed the constraint and tries others.
    - The algorithm records the path with the most visited airports found so far.

    Why DFS and not BFS?
        BFS explores level by level (fewest hops first). It would find paths
        with fewest hops first, not the deepest paths within budget.
        DFS naturally digs deep — exactly what "visit maximum destinations"
        requires.

    Mapping from Grafos.ipynb → this implementation:
        no_visitados set  → visited set (same idea, inverted)
        arista.getPeso()  → edge_weight from _pick_best_aircraft (per criterion)
        dist[u] update    → resource_remaining decremented each hop
        pred dict         → legs list (backtracked on each return)

    Complexity: O(V!) worst case, but budget/time constraints prune branches
    heavily. With 31 airports and realistic costs, paths rarely exceed
    8-10 hops before hitting the constraint.
"""

import math
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.graph import Graph
from models.itinerary import Itinerary
from models.leg import Leg
from models.trip_config import TripConfig
from utils.constants import AIRCRAFT_RATES
from services.route_optimizer import _AIRCRAFT_NAME_MAP, _pick_best_aircraft


# ------------------------------------------------------------------ #
# Internal helpers                                                     #
# ------------------------------------------------------------------ #

def _rebuild_used_types(legs: List[Leg]) -> Set[str]:
    """Recompute the set of aircraft type keys from a list of legs.

    Called after backtracking to keep used_types consistent.
    A simple discard() would incorrectly remove a type still used
    by an earlier leg on the path.

    Args:
        legs: current legs on the active DFS path.

    Returns:
        Set of constants.py aircraft keys present in those legs.
    """
    return {
        _AIRCRAFT_NAME_MAP.get(leg.aircraft, leg.aircraft)
        for leg in legs
    }


def _dfs(
    graph: Graph,
    current_id: str,
    visited: Set[str],
    legs: List[Leg],
    used_types: Set[str],
    best: Dict[str, Any],
    weight_fn: Callable[[float, Dict], float],
    allowed_keys: Optional[Set[str]],
    include_secondary: bool,
    resource_remaining: float,
    required_types: Set[str],
) -> None:
    """Recursive DFS with backtracking — core of the planner.

    Mutates `legs`, `visited`, `used_types`, and `best` in place.
    All mutations are undone on backtrack (except `best` — it only grows).

    Args:
        graph:              live Graph built by GraphDataService.
        current_id:         airport currently being visited.
        visited:            IDs on the active path — no revisits allowed.
        legs:               legs accumulated so far (mutable, backtracked).
        used_types:         aircraft type keys used so far on this path.
        best:               mutable dict — updated whenever a better path is found.
        weight_fn:          (distance, rates_dict) → float edge weight.
        allowed_keys:       set of allowed aircraft keys; None = all allowed.
        include_secondary:  if False, skip non-hub intermediates.
        resource_remaining: budget (USD) or time (min) remaining before constraint.
        required_types:     aircraft type keys that must each appear at least once.
    """
    n = len(legs)  # destinations reached beyond origin
    uses_all = required_types.issubset(used_types)

    # Update best solution that satisfies the type constraint
    if uses_all and n > best["count"]:
        best["count"] = n
        best["legs"]  = list(legs)  # snapshot — legs will be mutated

    # Update best fallback (no type constraint) — used if no constrained path exists
    if n > best["fallback_count"]:
        best["fallback_count"] = n
        best["fallback_legs"]  = list(legs)

    # ── Explore neighbors ──────────────────────────────────────────
    for route in graph.get_neighbors(current_id):
        if bool(getattr(route, "blocked", False)):
            continue

        next_id = route.destination_vertex

        # No revisiting — project rule: no airport more than once as stopover
        if next_id in visited:
            continue

        # Hub filter: skip non-hub intermediates when requested
        if not include_secondary:
            airport = graph.get_vertex(next_id)
            if airport and not airport.is_hub:
                continue

        # Select best aircraft for this criterion on this route
        edge_weight, aircraft_name, aircraft_key = _pick_best_aircraft(
            route.aircrafts,
            route.distance,
            weight_fn,
            allowed_keys,
        )

        # No valid aircraft on this route for allowed types → skip
        if edge_weight == math.inf:
            continue

        # Prune: this leg would exceed the remaining resource
        if edge_weight > resource_remaining:
            continue

        # Build leg — always compute BOTH cost and time regardless of criterion
        # so the Itinerary can display both in the report (R5)
        rates = AIRCRAFT_RATES.get(aircraft_key, {})
        leg = Leg(
            origin_id       = current_id,
            destination_id  = next_id,
            aircraft        = aircraft_name,
            distance        = route.distance,
            flight_time_min = round(route.distance * rates.get("time_per_km_min", 0.0), 2),
            leg_cost        = round(route.distance * rates.get("cost_per_km",     0.0), 2),
        )

        # ── Go deeper ─────────────────────────────────────────────
        legs.append(leg)
        visited.add(next_id)
        used_types.add(aircraft_key)

        _dfs(
            graph              = graph,
            current_id         = next_id,
            visited            = visited,
            legs               = legs,
            used_types         = used_types,
            best               = best,
            weight_fn          = weight_fn,
            allowed_keys       = allowed_keys,
            include_secondary  = include_secondary,
            resource_remaining = resource_remaining - edge_weight,
            required_types     = required_types,
        )

        # ── Backtrack ─────────────────────────────────────────────
        legs.pop()
        visited.discard(next_id)
        # Rebuild used_types from remaining legs — simple discard() would
        # incorrectly remove a type still present in an earlier leg
        used_types.clear()
        used_types.update(_rebuild_used_types(legs))


def _assemble_itinerary(legs: List[Leg], criteria: str) -> Optional[Itinerary]:
    """Build an Itinerary from a flat list of Leg objects.

    Bypasses add_leg() connectivity validation intentionally — legs were
    built sequentially by the DFS so connectivity is guaranteed.

    Args:
        legs:     ordered list of Leg objects.
        criteria: optimization criterion stored in the Itinerary.

    Returns:
        Itinerary, or None if legs is empty (origin has no reachable airports).
    """
    if not legs:
        return None
    itin = Itinerary(optimization_criteria=criteria)
    for leg in legs:
        itin.legs.append(leg)
    return itin


# ------------------------------------------------------------------ #
# Public planner class                                                 #
# ------------------------------------------------------------------ #

class ItineraryPlanner:
    """Generates maximum-coverage itineraries from a single origin.

    Single Responsibility: explores the graph for maximum destination coverage.
    Does not load data, render UI, or generate reports.

    Dependency Inversion: receives Graph and TripConfig as parameters.
    Does not instantiate GraphDataService or know where the data came from.
    """

    def _resolve_required_types(
        self,
        allowed_keys: Optional[Set[str]],
        graph: Graph,
    ) -> Set[str]:
        """Find which aircraft types must appear at least once in the path.

        Only types that ACTUALLY EXIST on at least one route in the graph
        are required. Requiring 'propeller' when no route has propellers
        would make every possible path invalid.

        Args:
            allowed_keys: types the traveler allows (None = all).
            graph:        live graph to inspect.

        Returns:
            Set of aircraft type keys that must each be used at least once.
        """
        existing: Set[str] = set()
        for airport in graph.vertices:
            for route in airport.adjacencies:
                for name in route.aircrafts:
                    key = _AIRCRAFT_NAME_MAP.get(name)
                    if key:
                        existing.add(key)

        # Only require types the traveler is willing to use
        if allowed_keys is not None:
            existing &= allowed_keys

        return existing

    def _run_dfs(
        self,
        graph: Graph,
        origin: str,
        config: TripConfig,
        weight_fn: Callable[[float, Dict], float],
        resource_limit: float,
        criteria: str,
    ) -> Optional[Itinerary]:
        """Shared DFS runner used by both public plan methods.

        Args:
            graph:          live Graph.
            origin:         IATA departure code.
            config:         TripConfig with budget, time, transport preferences.
            weight_fn:      (distance, rates) → float, defines the edge weight.
            resource_limit: max budget (USD) or max time (min).
            criteria:       'cost' or 'time' — stored in the returned Itinerary.

        Returns:
            Best Itinerary found, or None if no valid path exists.
        """
        if origin not in graph:
            raise ValueError(f"Origin airport {origin!r} not found in graph.")

        allowed_keys: Optional[Set[str]] = (
            {_AIRCRAFT_NAME_MAP.get(t, t) for t in config.preferred_aircraft}
            if config.preferred_aircraft else None
        )
        required_types = self._resolve_required_types(allowed_keys, graph)

        best: Dict[str, Any] = {
            "count":          0,
            "legs":           [],
            "fallback_count": 0,
            "fallback_legs":  [],
        }

        _dfs(
            graph              = graph,
            current_id         = origin,
            visited            = {origin},
            legs               = [],
            used_types         = set(),
            best               = best,
            weight_fn          = weight_fn,
            allowed_keys       = allowed_keys,
            include_secondary  = config.allow_secondary_airports,
            resource_remaining = resource_limit,
            required_types     = required_types,
        )

        # Prefer path that satisfies the type constraint
        # Fall back to unconstrained best if no type-valid path was found
        winning_legs = best["legs"] if best["legs"] else best["fallback_legs"]
        return _assemble_itinerary(winning_legs, criteria)

    def plan_max_destinations_by_budget(
        self,
        graph: Graph,
        origin: str,
        config: TripConfig,
    ) -> Optional[Itinerary]:
        """Itinerary A — visit most destinations without exceeding budget.

        Uses cheapest aircraft per route (minimizes cost_per_km × distance).
        Resource limit: config.budget_initial in USD.

        Returns:
            Itinerary or None if no route is reachable within budget.
        """
        return self._run_dfs(
            graph          = graph,
            origin         = origin,
            config         = config,
            weight_fn      = lambda d, r: d * r.get("cost_per_km", math.inf),
            resource_limit = config.budget_initial,
            criteria       = "cost",
        )

    def plan_max_destinations_by_time(
        self,
        graph: Graph,
        origin: str,
        config: TripConfig,
    ) -> Optional[Itinerary]:
        """Itinerary B — visit most destinations within available time.

        Uses fastest aircraft per route (minimizes time_per_km_min × distance).
        Resource limit: config.time_available_h × 60 converted to minutes.

        Returns:
            Itinerary or None if no route is reachable within time limit.
        """
        return self._run_dfs(
            graph          = graph,
            origin         = origin,
            config         = config,
            weight_fn      = lambda d, r: d * r.get("time_per_km_min", math.inf),
            resource_limit = config.time_available_h * 60.0,
            criteria       = "time",
        )

    def plan_both(
        self,
        graph: Graph,
        origin: str,
        config: TripConfig,
    ) -> Tuple[Optional[Itinerary], Optional[Itinerary]]:
        """Run both plan variants in one call.

        Used by r2_routes.py to generate both alternatives for the API response.

        Returns:
            (itinerary_a, itinerary_b):
                itinerary_a = max destinations within budget (criteria='cost')
                itinerary_b = max destinations within time   (criteria='time')
        """
        return (
            self.plan_max_destinations_by_budget(graph, origin, config),
            self.plan_max_destinations_by_time(graph, origin, config),
        )