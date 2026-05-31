"""Abstract base class for all route optimizers.

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
    #All share the same optimize() method. Can use them interchangeably.

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Optimizer name returned in API response.
        Examples: 'cost', 'time', 'distance'.
        Used by frontend to label itineraries.
        """

    @abstractmethod
    def optimize(
        self,
        graph: Graph,
        origin: str,
        dest: str,
        transport_types: Optional[List[str]] = None,
        include_secondary: bool = True, #Exclude non-hub airports if False.
        **params: Any, # **params: Extra options (e.g. max_stops=2).
    ) -> Optional[Itinerary]:
        """Find the best route between origin and dest.
        """

    def validate_endpoints(self, graph: Graph, origin: str, dest: str) -> None:
        
        #Check that origin and dest exist in graph and are different.

        if origin not in graph:
            raise ValueError(f"Origin {origin!r} not found in graph.")
        if dest not in graph:
            raise ValueError(f"Destination {dest!r} not found in graph.")
        if origin == dest:
            raise ValueError(f"Origin and destination are the same: {origin!r}.")
