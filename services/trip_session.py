from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, TYPE_CHECKING
import uuid

from models.planner_models import (
    DecisionRecord,
    Leg,
    RouteProposal,
    TransportOption,
    TripConfig,
    TripState,
    StepProposalResult,
    ApplyResult,
    TripReport,
)
from utils.constants import GRAPH_CONFIG_DEFAULTS

if TYPE_CHECKING:
    from services.advanced_planner import AdvancedPlanner


class TripSession:
    """Represents a step-by-step interactive session.

    The UI should call ``step_proposals()`` and then ``apply_choice()``
    according to the traveler decision. Every decision is stored in
    ``state.decisions``.
    """

    def __init__(self, config: TripConfig, initial_state: TripState, planner: "AdvancedPlanner") -> None:
        self.config = config
        self.state = initial_state
        self.planner = planner
        self.session_id = str(uuid.uuid4())

    _AIRCRAFT_NAME_MAP: Dict[str, str] = {
        "Comercial": "commercial",
        "Regional": "regional",
        "Helice": "propeller",
        "Hélice": "propeller",
        "comercial": "commercial",
        "regional": "regional",
        "helice": "propeller",
        "hélice": "propeller",
        "commercial": "commercial",
        "propeller": "propeller",
    }

    def _serialize_item(self, item: Any) -> Any:
        if hasattr(item, "to_dict"):
            return item.to_dict()
        if is_dataclass(item):
            return asdict(item)
        return item

    def _resolved_aircraft_rates(self) -> Dict[str, Dict[str, float]]:
        base = {
            key: {
                "cost_per_km": float(value.get("costoKm", 0.0)),
                "time_per_km_min": float(value.get("tiempoKm", 0.0)),
            }
            for key, value in GRAPH_CONFIG_DEFAULTS.get("aeronaves", {}).items()
        }

        source_overrides: Dict[str, Any] = {}
        if isinstance(self.planner.defaults, dict):
            source_overrides.update(self.planner.defaults)
        if isinstance(self.config.global_overrides, dict):
            source_overrides.update(self.config.global_overrides)

        aircraft_overrides = source_overrides.get("aeronaves", {})
        if isinstance(aircraft_overrides, dict):
            for aircraft_key, values in aircraft_overrides.items():
                if not isinstance(values, dict):
                    continue
                normalized_key = self._AIRCRAFT_NAME_MAP.get(aircraft_key, aircraft_key)
                current = dict(base.get(normalized_key, {}))
                if "costoKm" in values:
                    current["cost_per_km"] = float(values["costoKm"])
                if "tiempoKm" in values:
                    current["time_per_km_min"] = float(values["tiempoKm"])
                base[normalized_key] = current

        return base

    def calculate_tramo(self, distance_km: float, tipo_aeronave: str, es_subsidiada: bool) -> Dict[str, Any]:
        """Pure segment calculator for phase 1.

        It computes cost/time and validates the subsidized distance rule.
        """
        if distance_km < 0:
            return {"ok": False, "error": "distance_km must be >= 0"}

        aircraft_key = self._AIRCRAFT_NAME_MAP.get(tipo_aeronave, tipo_aeronave)
        rates = self._resolved_aircraft_rates().get(aircraft_key)
        if not rates:
            return {"ok": False, "error": f"Unknown aircraft type: {tipo_aeronave}"}

        time_min = int(round(float(distance_km) * float(rates.get("time_per_km_min", 0.0))))
        cost_usd = 0.0 if es_subsidiada else round(float(distance_km) * float(rates.get("cost_per_km", 0.0)), 2)

        new_total_distance = self.state.distance_travelled_km + float(distance_km)
        new_subsidized_distance = self.state.subsidized_distance_km + (float(distance_km) if es_subsidiada else 0.0)
        max_subsidized_fraction = float(self.state.subsidized_distance_limit_frac)

        if new_total_distance > 0 and (new_subsidized_distance / new_total_distance) > max_subsidized_fraction:
            max_allowed = round(new_total_distance * max_subsidized_fraction, 2)
            return {
                "ok": False,
                "error": (
                    "Subsidized distance limit exceeded. "
                    f"Allowed up to {max_allowed} km, projected {round(new_subsidized_distance, 2)} km."
                ),
            }

        return {
            "ok": True,
            "distance_km": float(distance_km),
            "aircraft": tipo_aeronave,
            "aircraft_key": aircraft_key,
            "is_subsidized": es_subsidiada,
            "cost_usd": cost_usd,
            "time_min": time_min,
        }

    def step_proposals(self) -> StepProposalResult:
        """Compute and return current alternatives.

        It should include:
        - candidate routes from ``state.current_airport``
        - transport options per route
        - available activities and jobs
        - markers for mandatory actions (lodging/meals)
        """
        routes: List[RouteProposal] = []
        activities: List[Any] = []
        jobs: List[Any] = []

        current_airport = self.planner.graph.get_vertex(self.state.current_airport)
        if current_airport is not None:
            activities = list(getattr(current_airport, "activities", []))
            jobs = list(getattr(current_airport, "jobs", []))

        for route in self.planner.graph.get_neighbors(self.state.current_airport):
            route_is_subsidized = float(getattr(route, "cost", 0.0)) == 0.0
            options: List[TransportOption] = []

            for aircraft in getattr(route, "aircrafts", []):
                calc = self.calculate_tramo(route.distance, aircraft, route_is_subsidized)
                if not calc.get("ok"):
                    continue
                options.append(
                    TransportOption(
                        aircraft=aircraft,
                        cost_usd=float(calc["cost_usd"]),
                        time_min=int(calc["time_min"]),
                        is_subsidized=route_is_subsidized,
                    )
                )

            if not options:
                continue

            routes.append(
                RouteProposal(
                    id=f"{self.state.current_airport}->{route.destination_vertex}",
                    destination=route.destination_vertex,
                    distance_km=float(route.distance),
                    transport_options=options,
                    est_arrival_min=self.state.time_elapsed_min + min(o.time_min for o in options),
                )
            )

        return StepProposalResult(
            routes=routes,
            activities=activities,
            jobs=jobs,
            mandatory_actions=[],
            meta={
                "phase": 1,
                "session_id": self.session_id,
                "current_airport": self.state.current_airport,
                "budget_remaining": self.state.budget_remaining,
                "time_remaining_min": self.state.time_remaining_min,
                "distance_travelled_km": self.state.distance_travelled_km,
                "subsidized_distance_km": self.state.subsidized_distance_km,
            },
        )

    def apply_choice(self, choice: Dict[str, Any]) -> ApplyResult:
        """Apply a user decision and update ``TripState``.

        ``choice`` is a dict carrying the decision
        (transport/activity/job/skip).
        Returns ``ApplyResult`` with the updated state and next proposals.
        """
        kind = (choice.get("kind") or choice.get("type") or "").lower()
        if kind != "transport":
            return ApplyResult(
                updated_state=self.state,
                errors=["Phase 1 only supports kind='transport'."],
            )

        destination = choice.get("destination")
        aircraft = choice.get("aircraft")
        if not destination or not aircraft:
            return ApplyResult(
                updated_state=self.state,
                errors=["transport choice requires destination and aircraft"],
            )

        selected_route = None
        for route in self.planner.graph.get_neighbors(self.state.current_airport):
            if route.destination_vertex == destination:
                selected_route = route
                break

        if selected_route is None:
            return ApplyResult(
                updated_state=self.state,
                errors=[f"No route from {self.state.current_airport} to {destination}"],
            )

        if aircraft not in getattr(selected_route, "aircrafts", []):
            return ApplyResult(
                updated_state=self.state,
                errors=[f"Aircraft {aircraft!r} is not available for this route"],
            )

        is_subsidized = float(getattr(selected_route, "cost", 0.0)) == 0.0
        calc = self.calculate_tramo(selected_route.distance, aircraft, is_subsidized)
        if not calc.get("ok"):
            return ApplyResult(updated_state=self.state, errors=[str(calc.get("error"))])

        cost_usd = float(calc["cost_usd"])
        time_min = int(calc["time_min"])

        if cost_usd > self.state.budget_remaining:
            return ApplyResult(
                updated_state=self.state,
                errors=["Budget exceeded for selected transport option"],
            )
        if time_min > self.state.time_remaining_min:
            return ApplyResult(
                updated_state=self.state,
                errors=["Not enough remaining time for selected transport option"],
            )

        self.state.budget_remaining = round(self.state.budget_remaining - cost_usd, 2)
        self.state.time_elapsed_min += time_min
        self.state.time_remaining_min -= time_min
        self.state.distance_travelled_km += float(selected_route.distance)
        if is_subsidized:
            self.state.subsidized_distance_km += float(selected_route.distance)

        leg = Leg(
            origin_id=self.state.current_airport,
            destination_id=destination,
            aircraft=aircraft,
            distance=float(selected_route.distance),
            flight_time_min=float(time_min),
            leg_cost=float(cost_usd),
        )
        self.state.itinerary.append(leg)
        self.state.current_airport = destination

        self.state.decisions.append(
            DecisionRecord(
                timestamp_min=self.state.time_elapsed_min,
                kind="transport",
                details={
                    "origin": leg.origin_id,
                    "destination": leg.destination_id,
                    "aircraft": leg.aircraft,
                    "distance_km": leg.distance,
                    "time_min": leg.flight_time_min,
                    "cost_usd": leg.leg_cost,
                    "is_subsidized": is_subsidized,
                },
            )
        )

        return ApplyResult(
            updated_state=self.state,
            next_proposals=self.step_proposals(),
            events=[f"Flight applied: {leg.origin_id} -> {leg.destination_id} ({leg.aircraft})"],
            errors=[],
        )

    def serialize(self) -> Dict[str, Any]:
        """Serialize session state for persistence (save/restore)."""
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
        """Restore a ``TripSession`` from serialized data."""
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
            itinerary=[Leg.from_dict(leg) if isinstance(leg, dict) else leg for leg in state_data.get("itinerary", [])],
            activities_done=list(state_data.get("activities_done", [])),
            jobs_done=list(state_data.get("jobs_done", [])),
            last_accommodation_at_min=state_data.get("last_accommodation_at_min"),
            last_meal_at_min=state_data.get("last_meal_at_min"),
            decisions=list(state_data.get("decisions", [])),
        )

        session = TripSession(config=config, initial_state=state, planner=planner)
        if data.get("session_id"):
            session.session_id = str(data["session_id"])
        return session

    def force_recalculate_after_network_change(self, changed_edges: List[Any]) -> Dict[str, Any]:
        """Recompute proposals when network state changes (R4 integration).

        Should return metadata about recalculation and the new state.
        """
        return {
            "recalculated": True,
            "changed_edges": list(changed_edges),
            "current_airport": self.state.current_airport,
            "new_proposals": self.step_proposals(),
        }

    def finalize_and_report(self) -> TripReport:
        """Generate the final ``TripReport`` with totals and records.

        This method returns the report structure required by R5.
        """
        total_spent = round(self.state.budget_initial - self.state.budget_remaining, 2)
        return TripReport(
            visited=[],
            legs=list(self.state.itinerary),
            activities=list(self.state.activities_done),
            jobs=list(self.state.jobs_done),
            totals={
                "budget_initial": self.state.budget_initial,
                "total_spent": total_spent,
                "total_gained": 0.0,
                "final_balance": self.state.budget_remaining,
                "time_total_min": self.state.time_elapsed_min,
                "distance_travelled_km": round(self.state.distance_travelled_km, 2),
                "subsidized_distance_km": round(self.state.subsidized_distance_km, 2),
            },
        )


__all__ = ["TripSession"]
