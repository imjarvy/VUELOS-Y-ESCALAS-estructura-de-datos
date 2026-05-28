from __future__ import annotations

from typing import Any, Dict

from models.planner_models import ApplyResult, DecisionRecord, Leg


class TripSessionDecisionMixin:
    def apply_choice(self, choice: Dict[str, Any]) -> ApplyResult:
        kind = (choice.get("kind") or choice.get("type") or "").lower()
        if kind not in {"transport", "activity", "job"}:
            return ApplyResult(updated_state=self.state, errors=["Unsupported choice kind."])

        current_airport = self.planner.graph.get_vertex(self.state.current_airport)
        if current_airport is None:
            return ApplyResult(
                updated_state=self.state,
                errors=[f"Current airport {self.state.current_airport!r} not found"],
            )

        if kind == "activity":
            activity_ref = choice.get("activity") or choice.get("activity_id") or choice.get("id") or choice.get("name")
            selected_activity = None
            for activity in getattr(current_airport, "activities", []):
                if activity_ref in {getattr(activity, "id", None), getattr(activity, "name", None)}:
                    selected_activity = activity
                    break

            if selected_activity is None:
                return ApplyResult(
                    updated_state=self.state,
                    errors=[f"Activity {activity_ref!r} is not available at current airport"],
                )

            duration_min = int(getattr(selected_activity, "duration_min", 0))
            cost_usd = float(getattr(selected_activity, "cost_usd", 0.0))
            if cost_usd > self.state.budget_remaining:
                return ApplyResult(updated_state=self.state, errors=["Budget exceeded for selected activity"])
            if duration_min > self.state.time_remaining_min:
                return ApplyResult(updated_state=self.state, errors=["Not enough remaining time for selected activity"])

            self.state.budget_remaining = round(self.state.budget_remaining - cost_usd, 2)
            trigger_events = self.advance_time(
                duration_min,
                is_flight=False,
                meal_airport_id=self.state.current_airport,
            )
            performed_at_min = self.state.time_elapsed_min
            activity_record = {
                "kind": "activity",
                "name": getattr(selected_activity, "name", activity_ref),
                "airport_id": self.state.current_airport,
                "performed_at_min": performed_at_min,
                "cost_usd": cost_usd,
                "duration_min": duration_min,
                "activity_type": getattr(selected_activity, "type", "optional"),
            }
            self.state.activities_done.append(activity_record)
            self.state.decisions.append(
                DecisionRecord(
                    timestamp_min=performed_at_min,
                    kind="activity",
                    details={
                        "activity_id": getattr(selected_activity, "id", activity_ref),
                        "name": getattr(selected_activity, "name", activity_ref),
                        "airport_id": self.state.current_airport,
                        "duration_min": duration_min,
                        "cost_usd": cost_usd,
                    },
                )
            )

            return ApplyResult(
                updated_state=self.state,
                next_proposals=self.step_proposals(),
                events=[f"Activity applied: {activity_record['name']}", *trigger_events],
                errors=[],
            )

        if kind == "job":
            job_ref = choice.get("job") or choice.get("job_id") or choice.get("id") or choice.get("name")
            selected_job = None
            for job in getattr(current_airport, "jobs", []):
                if job_ref in {getattr(job, "id", None), getattr(job, "name", None)}:
                    selected_job = job
                    break

            if selected_job is None:
                return ApplyResult(
                    updated_state=self.state,
                    errors=[f"Job {job_ref!r} is not available at current airport"],
                )

            if self.state.budget_remaining >= (self.state.budget_initial * 0.35):
                return ApplyResult(
                    updated_state=self.state,
                    errors=["Job can only be accepted when budget is below 35% of the initial budget"],
                )

            hours_worked = float(choice.get("hours") or choice.get("hours_worked") or 0)
            if hours_worked <= 0:
                return ApplyResult(updated_state=self.state, errors=["hours worked must be greater than zero"])

            max_hours = float(getattr(selected_job, "max_hours", 0))
            available_hours = self.state.time_remaining_min / 60.0
            if hours_worked > max_hours:
                return ApplyResult(updated_state=self.state, errors=["Requested hours exceed the job maximum"])
            if hours_worked > available_hours:
                return ApplyResult(updated_state=self.state, errors=["Requested hours exceed the remaining travel time"])

            income_usd = round(float(getattr(selected_job, "hourly_rate", 0.0)) * hours_worked, 2)
            minutes_worked = int(round(hours_worked * 60.0))
            self.state.budget_remaining = round(self.state.budget_remaining + income_usd, 2)
            trigger_events = self.advance_time(
                minutes_worked,
                is_flight=False,
                meal_airport_id=self.state.current_airport,
            )
            performed_at_min = self.state.time_elapsed_min
            job_record = {
                "kind": "job",
                "name": getattr(selected_job, "name", job_ref),
                "airport_id": self.state.current_airport,
                "performed_at_min": performed_at_min,
                "hours_worked": hours_worked,
                "income_usd": income_usd,
                "max_hours": max_hours,
            }
            self.state.jobs_done.append(job_record)
            self.state.decisions.append(
                DecisionRecord(
                    timestamp_min=performed_at_min,
                    kind="job",
                    details={
                        "job_id": getattr(selected_job, "id", job_ref),
                        "name": getattr(selected_job, "name", job_ref),
                        "airport_id": self.state.current_airport,
                        "hours_worked": hours_worked,
                        "income_usd": income_usd,
                    },
                )
            )

            return ApplyResult(
                updated_state=self.state,
                next_proposals=self.step_proposals(),
                events=[f"Job applied: {job_record['name']}", *trigger_events],
                errors=[],
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
            return ApplyResult(updated_state=self.state, errors=["Budget exceeded for selected transport option"])
        if time_min > self.state.time_remaining_min:
            return ApplyResult(updated_state=self.state, errors=["Not enough remaining time for selected transport option"])

        self.state.budget_remaining = round(self.state.budget_remaining - cost_usd, 2)
        trigger_events = self.advance_time(
            time_min,
            is_flight=True,
            meal_airport_id=self.state.current_airport,
        )
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
        trigger_events.extend(self.settle_lodging_after_landing())

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
            events=[f"Flight applied: {leg.origin_id} -> {leg.destination_id} ({leg.aircraft})", *trigger_events],
            errors=[],
        )