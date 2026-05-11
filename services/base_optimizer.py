"""Abstract base class for all route optimizers (R2).

Open/Closed Principle in practice:
    This file defines the contract. Adding a new optimization criterion
    (e.g. fewest stops) means creating a new subclass — not modifying
    this file or any existing optimizer.

Interface Segregation in practice:
    This interface only exposes what the UI layer needs: optimize() and name.
    It does not mix in report generation, data loading, or visualization.

Dependency Inversion in practice:
    planner_panel.js calls POST /api/plan/basic.
    r2_routes.py receives a BaseOptimizer instance (injected in app.py).
    The endpoint calls optimizer.optimize(...) without knowing whether
    it's running Dijkstra by cost, time, or distance.
    The UI depends on the abstraction, not the concrete implementation.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from core.graph import Graph
from models.itinerary import Itinerary


class BaseOptimizer(ABC):
    """Contract that every route optimizer must fulfill.

    Subclasses in route_optimizer.py (R2):
        CostOptimizer      — Dijkstra weighted by leg_cost (USD)
        TimeOptimizer      — Dijkstra weighted by flight_time_min
        DistanceOptimizer  — Dijkstra weighted by distance (km)

    All three implement the same optimize() signature so r2_routes.py
    can call them interchangeably based on the criteria the user selected
    in the frontend checkboxes.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable optimizer name returned in the API response.

        Examples: 'cost', 'time', 'distance'
        Used by the frontend to label each itinerary alternative.
        """

    @abstractmethod
    def optimize(
        self,
        graph: Graph,
        origin: str,
        dest: str,
        transport_types: Optional[List[str]] = None,
        include_secondary: bool = True,
        **params: Any,
    ) -> Optional[Itinerary]:
        """Compute the optimal route from origin to dest on the given graph.

        This is the only method r2_routes.py calls. It knows nothing about
        how the optimizer works internally — only that it receives a graph
        and returns an Itinerary (or None if no valid path exists).

        Args:
            graph:
                The live Graph instance loaded from airports.json.
                Already has blocked edges removed (R4 calls remove_edge
                before R2 recalculates).
            origin:
                IATA code of the departure airport (e.g. 'BOG').
            dest:
                IATA code of the destination airport (e.g. 'LIM').
            transport_types:
                List of allowed aircraft type keys from constants.py
                (e.g. ['commercial', 'regional']).
                If None or empty, all aircraft types are allowed.
            include_secondary:
                If False, routes that pass through non-hub airports
                are excluded from consideration.
            **params:
                Reserved for future criteria (e.g. max_stops=2).
                Subclasses may read from params; they must ignore unknown keys.

        Returns:
            An Itinerary with the ordered legs of the optimal path,
            or None if no valid path exists within the given constraints.

        Raises:
            ValueError: if origin or dest are not found in the graph.
        """

    def validate_endpoints(self, graph: Graph, origin: str, dest: str) -> None:
        """Shared validation called by every subclass before running.

        Centralizing this here means no subclass forgets to check it,
        and the error message is always consistent across optimizers.

        Args:
            graph:  The graph to validate against.
            origin: IATA departure code.
            dest:   IATA arrival code.

        Raises:
            ValueError: if either airport is missing from the graph.
        """
        if origin not in graph:
            raise ValueError(
                f"Origin airport {origin!r} not found in graph. "
                f"Check the airport code or the loaded JSON."
            )
        if dest not in graph:
            raise ValueError(
                f"Destination airport {dest!r} not found in graph. "
                f"Check the airport code or the loaded JSON."
            )
        if origin == dest:
            raise ValueError(
                f"Origin and destination are the same airport: {origin!r}."
            )