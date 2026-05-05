from typing import List, Dict, Any, Optional

class Airport:
    """Airport model.

    Fields:
    - airport_id: str (IATA code, e.g. "BOG")
    - name: str
    - city: str
    - is_hub: bool
    - accommodation_cost: float (USD per night)
    - feeding_cost: float (USD per meal)
    - activities: list[dict]
    - jobs: list[dict]
    - adjacencies: list[Route] or list[dict] (in-memory outgoing routes)

    Useful methods:
    - add_adjacency(route): add a route object or dict
    - neighbors(): return list of neighbor airport IDs
    - to_dict()/from_dict(): serialization helpers
    """

    def __init__(
        self,
        airport_id: str,
        name: str,
        city: str,
        is_hub: bool = False,
        accommodation_cost: float = 0.0,
        feeding_cost: float = 0.0,
        activities: Optional[List[Dict[str, Any]]] = None,
        jobs: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        
        if not airport_id or not isinstance(airport_id, str):
            raise ValueError("airport_id debe ser un str no vacío")
        if accommodation_cost < 0:
            raise ValueError("accommodation_cost no puede ser negativo")
        if feeding_cost < 0:
            raise ValueError("feeding_cost no puede ser negativo")

        self.airport_id: str = airport_id
        self.name: str = name
        self.city: str = city
        self.is_hub: bool = bool(is_hub)
        self.accommodation_cost: float = float(accommodation_cost)
        self.feeding_cost: float = float(feeding_cost)
        self.activities: List[Dict[str, Any]] = list(activities) if activities else []
        self.jobs: List[Dict[str, Any]] = list(jobs) if jobs else []
        self.adjacencies: List[Any] = []

    def add_adjacency(self, route: Any) -> None:
        """Add an outgoing route to this airport.

        Args:
            route: Route object, dict with route data, or a neighbor airport id.

        Raises:
            ValueError: if `route` is None.
        """
        if route is None:
            raise ValueError("route no puede ser None")
        self.adjacencies.append(route)

    def neighbors(self) -> List[str]:
        """Return neighbor airport IDs based on `adjacencies`.

        The method handles Route-like objects (with `origin_vertex`/`destination_vertex`
        or `origin_id`/`destination_id`), dicts with those keys, or plain string ids.
        """
        neighbors: List[str] = []
        for r in self.adjacencies:
            # objeto con atributos
            if hasattr(r, "origin_id") and hasattr(r, "destination_id"):
                if getattr(r, "origin_id") == self.airport_id:
                    neighbors.append(getattr(r, "destination_id"))
                else:
                    neighbors.append(getattr(r, "origin_id"))
                continue

            # dict con claves
            if isinstance(r, dict):
                ori = r.get("origin_id") or r.get("origen")
                dst = r.get("destination_id") or r.get("destino")
                if ori == self.airport_id and dst:
                    neighbors.append(dst)
                elif dst == self.airport_id and ori:
                    neighbors.append(ori)
                continue

            # fallback: si es string asumimos que es un id
            if isinstance(r, str):
                neighbors.append(r)

        return neighbors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the airport to a plain dict.

        Adjacencies are serialized via their `to_dict()` if available.
        """
        return {
            "airport_id": self.airport_id,
            "name": self.name,
            "city": self.city,
            "is_hub": self.is_hub,
            "accommodation_cost": self.accommodation_cost,
            "feeding_cost": self.feeding_cost,
            "activities": list(self.activities),
            "jobs": list(self.jobs),
            "adjacencies": [r.to_dict() if hasattr(r, "to_dict") else r for r in self.adjacencies],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Airport":
        """Create an `Airport` instance from a mapping (dict).

        The factory accepts several key names (English/Spanish) for flexibility.
        If `adjacencies` contains route dicts and `Route.from_dict` is importable,
        it will convert them to `Route` objects.
        """
        airport = cls(
            airport_id=data.get("airport_id") or data.get("id") or "",
            name=data.get("name") or data.get("nombre") or "",
            city=data.get("city") or data.get("ciudad") or "",
            is_hub=data.get("is_hub") or data.get("esHub") or False,
            accommodation_cost=data.get("accommodation_cost") or data.get("costoAlojamiento") or 0.0,
            feeding_cost=data.get("feeding_cost") or data.get("costoAlimentacion") or 0.0,
            activities=data.get("activities") or data.get("actividades") or [],
            jobs=data.get("jobs") or data.get("trabajos") or [],
        )

        # Cargar adyacencias si vienen como dicts
        adj = data.get("adjacencies") or data.get("adyacencias") or []
        for r in adj:
            if isinstance(r, dict):
                try:
                    from .route import Route

                    airport.adjacencies.append(Route.from_dict(r))
                except Exception:
                    airport.adjacencies.append(r)
            else:
                airport.adjacencies.append(r)

        return airport

    def __repr__(self) -> str:
        """Return a short representation useful for debugging."""
        return f"Airport({self.airport_id!r}, {self.name!r})"