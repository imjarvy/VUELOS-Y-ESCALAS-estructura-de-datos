from typing import List, Dict, Any, Optional


class Leg:
    """Represents a single flight segment between two airports.

    Cost and flight time are pre-calculated (distance × aircraft rate)
    and stored here so the API can return them without recalculating.

    Why a separate class and not a dict?
    - Validation on construction (no negative distances or costs).
    - to_dict() keeps the serialization format in one place.
    - route_optimizer.py builds Leg objects; report_generator.py reads them.
      Neither needs to know how the other works (Dependency Inversion).
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
        self.aircraft: str = aircraft            # e.g. "Avion Comercial"
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


class Itinerary:
    """Complete ordered sequence of flight legs representing a trip plan.

    This is the output of route_optimizer.py and itinerary_planner.py (R2),
    and the main input for report_generator.py (R5).

    Key design decision — totals as @property, not stored attributes:
        total_cost and total_time_min are computed from self.legs on demand.
        This means they are always consistent: add a leg and the totals
        update automatically. Storing them separately would require
        keeping them in sync manually, which is a common source of bugs.

    Key design decision — add_leg validates connectivity:
        The itinerary must be a connected path (A→B→C, never A→C with B missing).
        This is enforced in add_leg() so route_optimizer.py cannot accidentally
        build a disconnected itinerary.
    """

    VALID_CRITERIA = {"cost", "time", "distance"}

    def __init__(
        self,
        optimization_criteria: str = "cost",
        legs: Optional[List[Leg]] = None,
    ) -> None:
        """
        Args:
            optimization_criteria: what this itinerary was optimized for.
                                   Must be 'cost', 'time', or 'distance'.
            legs: optional initial list of Leg objects. Defaults to empty list.
        """
        if optimization_criteria not in self.VALID_CRITERIA:
            raise ValueError(
                f"optimization_criteria must be one of {self.VALID_CRITERIA}, "
                f"got {optimization_criteria!r}"
            )

        self.optimization_criteria: str = optimization_criteria
        self.legs: List[Leg] = list(legs) if legs else []

    # ------------------------------------------------------------------ #
    # Computed properties — always derived from self.legs                  #
    # ------------------------------------------------------------------ #

    @property
    def total_cost(self) -> float:
        """Total USD cost: sum of every leg's leg_cost."""
        return sum(leg.leg_cost for leg in self.legs)

    @property
    def total_time_min(self) -> float:
        """Total flight time in minutes: sum of every leg's flight_time_min."""
        return sum(leg.flight_time_min for leg in self.legs)

    @property
    def visited_airports(self) -> List[str]:
        """Ordered list of airport IDs touched during the trip.

        Always: [origin_of_first_leg, dest_of_leg_1, dest_of_leg_2, ...]
        Example: BOG → MDE → LIM  returns ["BOG", "MDE", "LIM"]
        """
        if not self.legs:
            return []
        result = [self.legs[0].origin_id]
        for leg in self.legs:
            result.append(leg.destination_id)
        return result

    # ------------------------------------------------------------------ #
    # Mutation                                                             #
    # ------------------------------------------------------------------ #

    def add_leg(self, leg: Leg) -> None:
        """Append a flight leg and enforce path connectivity.

        The new leg's origin must match the last leg's destination.
        A→B then C→D is invalid; A→B then B→C is valid.

        Args:
            leg: Leg object to append.

        Raises:
            TypeError: if leg is not a Leg instance.
            ValueError: if the leg breaks path connectivity.
        """
        if not isinstance(leg, Leg):
            raise TypeError(f"Expected a Leg instance, got {type(leg).__name__!r}")

        if self.legs and leg.origin_id != self.legs[-1].destination_id:
            raise ValueError(
                f"Connectivity error: new leg departs from {leg.origin_id!r} "
                f"but the last destination is {self.legs[-1].destination_id!r}."
            )

        self.legs.append(leg)

    # ------------------------------------------------------------------ #
    # Serialization                                                        #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full itinerary for the REST API (R2 and R5).

        Note: totals are rounded to 2 decimal places for clean JSON output.
        visited_airports is included so the frontend can highlight the route
        on the D3 graph without recalculating it.
        """
        return {
            "optimization_criteria": self.optimization_criteria,
            "legs": [leg.to_dict() for leg in self.legs],
            "total_cost": round(self.total_cost, 2),
            "total_time_min": round(self.total_time_min, 2),
            "visited_airports": self.visited_airports,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Itinerary":
        """Reconstruct an Itinerary from a plain dict.

        Used when restoring session state or deserializing an API response.
        """
        raw_legs = data.get("legs", [])
        legs = [Leg.from_dict(l) for l in raw_legs]
        return cls(
            optimization_criteria=data.get("optimization_criteria", "cost"),
            legs=legs,
        )

    def __repr__(self) -> str:
        return (
            f"Itinerary(criteria={self.optimization_criteria!r}, "
            f"legs={len(self.legs)}, "
            f"cost=${self.total_cost:.2f}, "
            f"time={self.total_time_min:.0f}min, "
            f"airports={self.visited_airports})"
        )