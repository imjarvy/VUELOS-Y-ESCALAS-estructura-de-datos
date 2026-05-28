from __future__ import annotations

from typing import Any, Dict

from models.planner_models import DecisionRecord, Leg, TripConfig, TripState

from services.trip_session_utils import serialize_item


class TripSessionPersistenceMixin:
    def _serialize_item(self, item: Any) -> Any:
        return serialize_item(item)

    def serialize(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "config": {
                "budget_initial": self.config.budget_initial,
                "time_available_h": self.config.time_available_h,
                "preferred_aircraft": list(self.config.preferred_aircraft),
                "allow_secondary_airports": self.config.allow_secondary_airports,
                "budget_threshold_pct": self.config.budget_threshold_pct,
                "global_overrides": dict(self.config.global_overrides),
            },
            "state": {
                "current_airport": self.state.current_airport,
                "budget_remaining": self.state.budget_remaining,
                "time_elapsed_min": self.state.time_elapsed_min,
                "time_remaining_min": self.state.time_remaining_min,
                "budget_initial": self.state.budget_initial,
                "time_total_min": self.state.time_total_min,
                "distance_travelled_km": self.state.distance_travelled_km,
                "subsidized_distance_km": self.state.subsidized_distance_km,
                "subsidized_distance_limit_frac": self.state.subsidized_distance_limit_frac,
                "meal_accumulated_min": self.state.meal_accumulated_min,
                "lodging_accumulated_min": self.state.lodging_accumulated_min,
                "lodging_pending_after_flight": self.state.lodging_pending_after_flight,
                "itinerary": [self._serialize_item(leg) for leg in self.state.itinerary],
                "activities_done": [self._serialize_item(a) for a in self.state.activities_done],
                "jobs_done": [self._serialize_item(j) for j in self.state.jobs_done],
                "last_accommodation_at_min": self.state.last_accommodation_at_min,
                "last_meal_at_min": self.state.last_meal_at_min,
                "decisions": [self._serialize_item(d) for d in self.state.decisions],
            },
        }

    @staticmethod
    def deserialize(data: Dict[str, Any], planner: "AdvancedPlanner") -> "TripSession":
        from services.trip_session import TripSession

        config_data = data.get("config", {})
        state_data = data.get("state", {})

        config = TripConfig(
            budget_initial=float(config_data.get("budget_initial", 0.0)),
            time_available_h=float(config_data.get("time_available_h", 0.0)),
            preferred_aircraft=list(config_data.get("preferred_aircraft", [])),
            allow_secondary_airports=bool(config_data.get("allow_secondary_airports", True)),
            budget_threshold_pct=float(config_data.get("budget_threshold_pct", 35.0)),
            global_overrides=dict(config_data.get("global_overrides", {})),
        )

        state = TripState(
            current_airport=str(state_data.get("current_airport", "")),
            budget_remaining=float(state_data.get("budget_remaining", 0.0)),
            time_elapsed_min=int(state_data.get("time_elapsed_min", 0)),
            time_remaining_min=int(state_data.get("time_remaining_min", 0)),
            budget_initial=float(state_data.get("budget_initial", 0.0)),
            time_total_min=int(state_data.get("time_total_min", 0)),
            distance_travelled_km=float(state_data.get("distance_travelled_km", 0.0)),
            subsidized_distance_km=float(state_data.get("subsidized_distance_km", 0.0)),
            subsidized_distance_limit_frac=float(state_data.get("subsidized_distance_limit_frac", 0.20)),
            meal_accumulated_min=int(state_data.get("meal_accumulated_min", 0)),
            lodging_accumulated_min=int(state_data.get("lodging_accumulated_min", 0)),
            lodging_pending_after_flight=bool(state_data.get("lodging_pending_after_flight", False)),
            itinerary=[Leg.from_dict(leg) if isinstance(leg, dict) else leg for leg in state_data.get("itinerary", [])],
            activities_done=list(state_data.get("activities_done", [])),
            jobs_done=list(state_data.get("jobs_done", [])),
            last_accommodation_at_min=state_data.get("last_accommodation_at_min"),
            last_meal_at_min=state_data.get("last_meal_at_min"),
            decisions=[DecisionRecord(**d) if isinstance(d, dict) else d for d in state_data.get("decisions", [])],
        )

        session = TripSession(config=config, initial_state=state, planner=planner)
        if data.get("session_id"):
            session.session_id = str(data["session_id"])
        return session