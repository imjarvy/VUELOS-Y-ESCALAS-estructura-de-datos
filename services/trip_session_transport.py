from __future__ import annotations

from typing import Any, Dict, List

from models.planner_models import ApplyResult, Leg, RouteProposal, StepProposalResult, TransportOption
from utils.constants import GRAPH_CONFIG_DEFAULTS

from services.trip_session_utils import AIRCRAFT_NAME_MAP, normalize_aircraft_name


class TripSessionTransportMixin:
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
                normalized_key = normalize_aircraft_name(aircraft_key)
                current = dict(base.get(normalized_key, {}))
                if "costoKm" in values:
                    current["cost_per_km"] = float(values["costoKm"])
                if "tiempoKm" in values:
                    current["time_per_km_min"] = float(values["tiempoKm"])
                base[normalized_key] = current

        return base

    def calculate_tramo(self, distance_km: float, tipo_aeronave: str, es_subsidiada: bool) -> Dict[str, Any]:
        if distance_km < 0:
            return {"ok": False, "error": "distance_km must be >= 0"}

        aircraft_key = AIRCRAFT_NAME_MAP.get(tipo_aeronave, tipo_aeronave)
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

        intervals = self._resolved_intervals_min()
        mandatory_actions: List[str] = []
        if self.state.lodging_pending_after_flight:
            mandatory_actions.append("lodging_pending_after_flight")
        if self.state.meal_accumulated_min >= intervals["meal_min"]:
            mandatory_actions.append("meal_due")
        if self.state.lodging_accumulated_min >= intervals["lodging_min"]:
            mandatory_actions.append("lodging_due")

        return StepProposalResult(
            routes=routes,
            activities=activities,
            jobs=jobs,
            mandatory_actions=mandatory_actions,
            meta={
                "phase": 2,
                "session_id": self.session_id,
                "current_airport": self.state.current_airport,
                "budget_remaining": self.state.budget_remaining,
                "time_remaining_min": self.state.time_remaining_min,
                "distance_travelled_km": self.state.distance_travelled_km,
                "subsidized_distance_km": self.state.subsidized_distance_km,
                "meal_accumulated_min": self.state.meal_accumulated_min,
                "lodging_accumulated_min": self.state.lodging_accumulated_min,
                "lodging_pending_after_flight": self.state.lodging_pending_after_flight,
            },
        )