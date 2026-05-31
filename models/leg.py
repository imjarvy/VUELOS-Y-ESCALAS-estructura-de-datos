from typing import Dict, Any


class Leg:
    """Represents a single flight segment between two airports.

    Cost and flight time are pre-calculated (distance × aircraft rate)
    and stored here so the API can return them without recalculating.

    """

    def __init__(
        self,
        origin_id: str,
        destination_id: str,
        aircraft: str,
        distance: float,
        flight_time_min: float,
        leg_cost: float,
    ) -> None:
        if not origin_id or not isinstance(origin_id, str):
            raise ValueError("origin_id must be a non-empty string")
        if not destination_id or not isinstance(destination_id, str):
            raise ValueError("destination_id must be a non-empty string")
        if distance < 0:
            raise ValueError("distance cannot be negative")
        if flight_time_min < 0:
            raise ValueError("flight_time_min cannot be negative")
        if leg_cost < 0:
            raise ValueError("leg_cost cannot be negative")

        self.origin_id: str = origin_id
        self.destination_id: str = destination_id
        self.aircraft: str = aircraft            # e.g. "Commercial"
        self.distance: float = float(distance)   # km
        self.flight_time_min: float = float(flight_time_min)
        self.leg_cost: float = float(leg_cost)   # USD

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this leg for the API response."""
        return {
            "origin_id": self.origin_id,
            "destination_id": self.destination_id,
            "aircraft": self.aircraft,
            "distance": self.distance,
            "flight_time_min": self.flight_time_min,
            "leg_cost": self.leg_cost,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Leg":
        """Reconstruct a Leg from a dict (e.g. from session state or API body)."""
        return cls(
            origin_id=data.get("origin_id", ""),
            destination_id=data.get("destination_id", ""),
            aircraft=data.get("aircraft", ""),
            distance=data.get("distance", 0.0),
            flight_time_min=data.get("flight_time_min", 0.0),
            leg_cost=data.get("leg_cost", 0.0),
        )

    def __repr__(self) -> str:
        return (
            f"Leg({self.origin_id!r} -> {self.destination_id!r}, "
            f"{self.aircraft}, ${self.leg_cost:.2f}, {self.flight_time_min:.0f}min)"
        )
