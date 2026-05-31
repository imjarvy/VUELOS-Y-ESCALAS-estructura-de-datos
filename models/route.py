from typing import List, Dict, Any, Optional


class Route:
    """Route model: connection between two airports.

    Fields:
    - origin_vertex: str (IATA code of origin)
    - destination_vertex: str (IATA code of destination)
    - distance: float
    - aircrafts: list[str]
    - cost: float (base cost)
    - minimum_stay: int (minimum stay at destination, minutes)
    - blocked: bool (route interruption flag)

    Methods:
    - to_dict()/from_dict(): serialization helpers
    """
    def __init__(
        self,
        origin_vertex: str,
        destination_vertex: str,
        distance: float,
        aircrafts: Optional[List[str]] = None,
        cost: float = 0.0,
        minimum_stay: int = 0,
        blocked: bool = False,
    ) -> None:
        """Initialize a Route and validate basic invariants.

        Raises ValueError for invalid inputs (empty IDs or negative numeric values).
        """
        if not origin_vertex or not isinstance(origin_vertex, str):
            raise ValueError("origin_id debe ser str no vacío")
        if not destination_vertex or not isinstance(destination_vertex, str):
            raise ValueError("destination_id debe ser str no vacío")
        if distance < 0:
            raise ValueError("distance_km no puede ser negativo")
        if minimum_stay < 0:
            raise ValueError("minimum_stay no puede ser negativo")

        self.origin_vertex: str = origin_vertex
        self.destination_vertex: str = destination_vertex
        self.distance: float = float(distance)
        self.aircrafts: List[str] = list(aircrafts) if aircrafts else []
        self.cost: float = float(cost)
        self.minimum_stay: int = int(minimum_stay)
        self.blocked: bool = bool(blocked)

    def to_dict(self) -> Dict[str, Any]:
        """Return a serializable dict representation of the route."""
        return {
            "origin_vertex": self.origin_vertex,
            "destination_vertex": self.destination_vertex,
            "distance": self.distance,
            "aircrafts": list(self.aircrafts),
            "cost": self.cost,
            "minimum_stay": self.minimum_stay,
            "blocked": self.blocked,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Route":
        """Create a Route from a mapping. Accepts English or Spanish keys (English priority)."""
        origin = data.get("origin") or data.get("origin_vertex") or ""
        dest = data.get("destination") or data.get("destination_vertex") or ""
        distance = data.get("distanceKm") or data.get("distance") or 0.0
        aircrafts = data.get("aircraft") or data.get("aircrafts") or []
        cost = data.get("baseCost") or data.get("cost") or 0.0
        minimum = data.get("minimumStay") or data.get("minimum_stay") or 0
        blocked = data.get("blocked") or data.get("isBlocked") or False
        return cls(origin, dest, distance, aircrafts=aircrafts, cost=cost, minimum_stay=minimum, blocked=blocked)

    def __repr__(self) -> str:
        """Short debug representation."""
        return f"Route({self.origin_vertex!r} -> {self.destination_vertex!r}, {self.distance}km, blocked={self.blocked})"
