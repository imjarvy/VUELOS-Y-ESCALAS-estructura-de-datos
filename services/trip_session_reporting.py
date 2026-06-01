from __future__ import annotations

from typing import Any, Dict, List

from models.planner_models import DecisionRecord, TripReport

from services.trip_session_utils import build_visited_from_legs, total_gained_from_jobs


class TripSessionReportingMixin:
    def procesar_interrupcion_vuelo(self, tramo: Any) -> List[str]:
        """Handle an in-flight interruption by sending the traveler back to the origin."""
        import random

        is_subsidized = float(getattr(tramo, "cost", 0.0)) == 0.0
        calc = self.calculate_tramo(
            tramo.distance,
            self.state.itinerary[-1].aircraft if self.state.itinerary else "Comercial",
            is_subsidized,
        )
        tiempo_vuelo = int(calc.get("time_min", 0))

        porcentaje_recorrido = random.uniform(0.3, 0.7)
        tiempo_ida = int(round(tiempo_vuelo * porcentaje_recorrido))
        tiempo_consumido = int(round(tiempo_ida * 2))

        trigger_events = self.advance_time(minutes=tiempo_consumido, is_flight=True, meal_airport_id=tramo.origen)

        self.state.current_airport = tramo.origen
        trigger_events.extend(self.settle_lodging_after_landing())

        self.state.decisions.append(
            DecisionRecord(
                timestamp_min=self.state.time_elapsed_min,
                kind="interruption",
                details={
                    "tramo_afectado": f"{tramo.origen}->{tramo.destination_vertex}",
                    "porcentaje_recorrido": round(porcentaje_recorrido, 2),
                    "tiempo_vuelo_min": tiempo_vuelo,
                    "tiempo_ida_min": tiempo_ida,
                    "tiempo_perdido_min": tiempo_consumido,
                    "regreso_a": tramo.origen,
                },
            )
        )

        return [f"¡Vuelo interrumpido al {int(porcentaje_recorrido * 100)}%! El viajero regresó a {tramo.origen}.", *trigger_events]

    def force_recalculate_after_network_change(self, changed_edges: List[Any]) -> Dict[str, Any]:
        """Rebuild the proposal list after a network change affects one or more routes."""
        return {
            "recalculated": True,
            "changed_edges": list(changed_edges),
            "current_airport": self.state.current_airport,
            "new_proposals": self.step_proposals(),
        }

    def finalize_and_report(self) -> TripReport:
        """Build the final trip report with visited airports, legs, activities, and totals."""
        visited = build_visited_from_legs(self.state.itinerary)
        total_gained = total_gained_from_jobs(self.state.jobs_done)
        total_spent = round(self.state.budget_initial + total_gained - self.state.budget_remaining, 2)

        return TripReport(
            visited=visited,
            legs=list(self.state.itinerary),
            activities=list(self.state.activities_done),
            jobs=list(self.state.jobs_done),
            totals={
                "budget_initial": self.state.budget_initial,
                "total_spent": total_spent,
                "total_gained": total_gained,
                "final_balance": self.state.budget_remaining,
                "time_total_min": self.state.time_elapsed_min,
                "distance_travelled_km": round(self.state.distance_travelled_km, 2),
                "subsidized_distance_km": round(self.state.subsidized_distance_km, 2),
            },
        )