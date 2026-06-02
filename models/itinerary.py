from typing import List, Dict, Any, Optional

from models.leg import Leg


class Itinerary:
    """Complete ordered sequence of flight legs representing a trip plan.
    This is the output of route_optimizer.py and itinerary_planner.py,
    and the main input for report_generator.py.
    """

    VALID_CRITERIA = {"cost", "time", "distance"}

    def __init__(
        self,
        optimization_criteria: str = "cost",
        legs: Optional[List[Leg]] = None,
     ) -> None:
        """
        Args:
            optimization_criteria: 'cost', 'time', or 'distance'.
            legs: optional initial list of Leg objects. Defaults to empty list.
        """
        if optimization_criteria not in self.VALID_CRITERIA:
            raise ValueError(
                f"optimization_criteria must be one of {self.VALID_CRITERIA}, "
                f"got {optimization_criteria!r}"
            )

        self.optimization_criteria: str = optimization_criteria
        self.legs: List[Leg] = list(legs) if legs else []

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
        Example: BOG -> MDE -> LIM  returns ["BOG", "MDE", "LIM"]
        """
        if not self.legs:
            return []
        result = [self.legs[0].origin_id]
        for leg in self.legs:
            result.append(leg.destination_id)
        return result

    def add_leg(self, leg: Leg) -> None:
        """Append a flight leg and enforce path connectivity.
          The new leg's origin must match the last leg's destination.
        A->B then C->D is invalid; A->B then B->C is valid.y.
        """
        if not isinstance(leg, Leg):
            raise TypeError(f"Expected a Leg instance, got {type(leg).__name__!r}")

        if self.legs and leg.origin_id != self.legs[-1].destination_id:
            raise ValueError(
                f"Connectivity error: new leg departs from {leg.origin_id!r} "
                f"but the last destination is {self.legs[-1].destination_id!r}."
            )

        self.legs.append(leg)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full itinerary for the REST API

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
        #Reconstruct an Itinerary from a plain dict.
        #Used when restoring session state or deserializing an API response.
        
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
