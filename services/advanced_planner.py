from __future__ import annotations
from typing import Optional, Any, Dict
from models.planner_models import (
    TripConfig,
    TripState,
)
from services.trip_session import TripSession
from utils.constants import DEFAULTS


class AdvancedPlanner:
    """
    Session manager for advanced planning.
    Receives a graph instance and exposes methods to start step-by-step sessions.
    """
    def __init__(self, graph: Any, defaults: Optional[Dict[str, Any]] = None) -> None:
        """Store the graph and the default configuration used to build sessions."""
        self.graph = graph
        self.defaults = defaults or {}

    def start_session(self, origin: str, budget: float, time_h: float, preferences: Optional[TripConfig] = None) -> "TripSession":
        """Create a new trip session with the initial budget, time, and planner state."""
        if not origin or origin not in self.graph:
            raise ValueError(f"Origin airport {origin!r} not found in graph.")
        if budget < 0:
            raise ValueError("Budget must be >= 0.")
        if time_h <= 0:
            raise ValueError("time_h must be > 0.")

        global_overrides = dict(self.defaults)
        budget_threshold = float(DEFAULTS["budget_threshold_pct"])

        if preferences is not None:
            budget_threshold = float(preferences.budget_threshold_pct)
            if isinstance(preferences.global_overrides, dict):
                global_overrides.update(preferences.global_overrides)

        config = TripConfig(
            budget_initial=float(budget),
            time_available_h=float(time_h),
            preferred_aircraft=list(preferences.preferred_aircraft) if preferences else [],
            allow_secondary_airports=preferences.allow_secondary_airports if preferences else True,
            budget_threshold_pct=budget_threshold,
            global_overrides=global_overrides,
        )

        state = TripState(
            current_airport=origin,
            budget_remaining=float(budget),
            time_elapsed_min=0,
            time_remaining_min=int(round(time_h * 60.0)),
            budget_initial=float(budget),
            time_total_min=int(round(time_h * 60.0)),
            distance_travelled_km=0.0,
            subsidized_distance_km=0.0,
            subsidized_distance_limit_frac=float(DEFAULTS["max_subsidized_distance_frac"]),
            free_time_min=0,
            current_stay_required_min=0,
            current_optional_stay_min=0,
            last_accommodation_at_min=0,
            last_meal_at_min=0,
        )

        return TripSession(config=config, initial_state=state, planner=self)


__all__ = [
    "AdvancedPlanner",
    "TripSession",
]
