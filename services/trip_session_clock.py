from __future__ import annotations

from typing import Any, Dict, List

from models.planner_models import DecisionRecord
from utils.constants import GRAPH_CONFIG_DEFAULTS


class TripSessionClockMixin:
    def _resolved_intervals_min(self) -> Dict[str, int]:
        """Resolve the meal and lodging intervals in minutes from the active configuration."""
        source_overrides: Dict[str, Any] = {}
        if isinstance(self.planner.defaults, dict):
            source_overrides.update(self.planner.defaults)
        if isinstance(self.config.global_overrides, dict):
            source_overrides.update(self.config.global_overrides)

        meal_h = float(source_overrides.get("intervaloAlimentacion", GRAPH_CONFIG_DEFAULTS.get("intervaloAlimentacion", 8.0)))
        lodging_h = float(source_overrides.get("intervaloAlojamiento", GRAPH_CONFIG_DEFAULTS.get("intervaloAlojamiento", 20.0)))

        return {
            "meal_min": max(1, int(round(meal_h * 60.0))),
            "lodging_min": max(1, int(round(lodging_h * 60.0))),
        }

    def _apply_mandatory_charge(self, *, airport_id: str, charge_kind: str, timestamp_min: int, interval_min: int) -> str:
        """Apply a mandatory meal or lodging charge and register the corresponding event."""
        airport = self.planner.graph.get_vertex(airport_id)
        if airport is None:
            return ""

        if charge_kind == "meal":
            amount = float(getattr(airport, "feeding_cost", 0.0))
            label = "Alimentación obligatoria"
            self.state.last_meal_at_min = timestamp_min
            reason = f"por haber transcurrido {max(1, int(round(interval_min / 60.0)))} horas desde la última comida"
        else:
            amount = float(getattr(airport, "accommodation_cost", 0.0))
            label = "Alojamiento obligatorio"
            self.state.last_accommodation_at_min = timestamp_min
            reason = f"por haber transcurrido {max(1, int(round(interval_min / 60.0)))} horas desde el último hospedaje"

        self.state.budget_remaining = round(self.state.budget_remaining - amount, 2)
        self.state.activities_done.append(
            {
                "kind": "mandatory",
                "name": label,
                "airport_id": airport_id,
                "performed_at_min": timestamp_min,
                "cost_usd": amount,
            }
        )
        self.state.decisions.append(
            DecisionRecord(
                timestamp_min=timestamp_min,
                kind="activity",
                details={
                    "mandatory": True,
                    "category": charge_kind,
                    "airport_id": airport_id,
                    "cost_usd": amount,
                },
            )
        )

        return f"{label} en {airport_id}: -${amount:.2f} {reason}."

    def advance_time(self, minutes: int, *, is_flight: bool, meal_airport_id: str) -> List[str]:
        """Advance the session clock and trigger meal or lodging rules when thresholds are reached."""
        if minutes < 0:
            raise ValueError("minutes must be >= 0")

        events: List[str] = []
        if minutes == 0:
            return events

        intervals = self._resolved_intervals_min()
        meal_interval = intervals["meal_min"]
        lodging_interval = intervals["lodging_min"]

        self.state.time_elapsed_min += int(minutes)
        self.state.time_remaining_min = max(0, self.state.time_remaining_min - int(minutes))
        self.state.meal_accumulated_min += int(minutes)
        self.state.lodging_accumulated_min += int(minutes)

        while self.state.meal_accumulated_min >= meal_interval:
            self.state.meal_accumulated_min -= meal_interval
            event_message = self._apply_mandatory_charge(
                airport_id=meal_airport_id,
                charge_kind="meal",
                timestamp_min=self.state.time_elapsed_min,
                interval_min=meal_interval,
            )
            if event_message:
                events.append(event_message)

        while self.state.lodging_accumulated_min >= lodging_interval:
            self.state.lodging_accumulated_min -= lodging_interval
            if is_flight:
                self.state.lodging_pending_after_flight = True
                events.append(
                    f"Alojamiento obligatorio pendiente en {meal_airport_id}: el tramo cruzó el umbral de {max(1, int(round(lodging_interval / 60.0)))} horas."
                )
            else:
                event_message = self._apply_mandatory_charge(
                    airport_id=self.state.current_airport,
                    charge_kind="lodging",
                    timestamp_min=self.state.time_elapsed_min,
                    interval_min=lodging_interval,
                )
                if event_message:
                    events.append(event_message)

        return events

    def settle_lodging_after_landing(self) -> List[str]:
        """Apply any lodging charge that remained pending after a flight landing."""
        if not self.state.lodging_pending_after_flight:
            return []

        intervals = self._resolved_intervals_min()
        event_message = self._apply_mandatory_charge(
            airport_id=self.state.current_airport,
            charge_kind="lodging",
            timestamp_min=self.state.time_elapsed_min,
            interval_min=intervals["lodging_min"],
        )
        self.state.lodging_pending_after_flight = False
        return [event_message] if event_message else []