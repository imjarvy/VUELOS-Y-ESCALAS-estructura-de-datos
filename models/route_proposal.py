from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Any, Dict

@dataclass
class RouteProposal:
    id: str
    destination: str
    distance_km: float
    transport_options: List[Any] = field(default_factory=list)
    est_arrival_min: int = 0
    minimum_stay_min: int = 0
    reachable_destinations: int = 0
    projected_budget_after_flight: float = 0.0
    projected_time_remaining_after_flight: int = 0
    estimated_job_income: float = 0.0
    priority_score: float = 0.0
    selection_reason: str = ""
