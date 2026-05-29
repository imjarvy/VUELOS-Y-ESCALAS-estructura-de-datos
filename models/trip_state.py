from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class TripState:
    current_airport: str
    budget_remaining: float
    time_elapsed_min: int
    time_remaining_min: int
    budget_initial: float = 0.0
    time_total_min: int = 0
    distance_travelled_km: float = 0.0
    subsidized_distance_km: float = 0.0
    subsidized_distance_limit_frac: float = 0.20
    free_time_min: int = 0
    current_stay_required_min: int = 0
    current_optional_stay_min: int = 0
    last_suggested_route: Optional[Dict[str, Any]] = None
    planned_route: List[Dict[str, Any]] = field(default_factory=list)
    meal_accumulated_min: int = 0
    lodging_accumulated_min: int = 0
    lodging_pending_after_flight: bool = False
    itinerary: List[Any] = field(default_factory=list)
    activities_done: List[Any] = field(default_factory=list)
    jobs_done: List[Any] = field(default_factory=list)
    last_accommodation_at_min: Optional[int] = None
    last_meal_at_min: Optional[int] = None
    decisions: List[Any] = field(default_factory=list)
