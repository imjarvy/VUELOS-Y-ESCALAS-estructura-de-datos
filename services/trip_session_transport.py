from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Tuple

from models.planner_models import ApplyResult, Leg, RouteProposal, StepProposalResult, TransportOption
from utils.constants import GRAPH_CONFIG_DEFAULTS

from services.trip_session_utils import AIRCRAFT_NAME_MAP, normalize_aircraft_name


class TripSessionTransportMixin:
    def _planning_settings(self) -> Dict[str, int]:
        """Resolve the route-planning limits used by the coverage beam search."""
        graph_size = max(1, len(getattr(self.planner.graph, "vertices", []) or []))

        source_overrides: Dict[str, Any] = {}
        if isinstance(self.planner.defaults, dict):
            source_overrides.update(self.planner.defaults)
        if isinstance(self.config.global_overrides, dict):
            source_overrides.update(self.config.global_overrides)

        def _int_setting(name: str, default_value: int) -> int:
            try:
                return int(source_overrides.get(name, default_value))
            except (TypeError, ValueError):
                return default_value

        return {
            "max_steps": min(18, max(6, max(_int_setting("route_plan_max_steps", 12), graph_size // 3))),
            "lookahead_depth": min(6, max(3, max(_int_setting("route_lookahead_depth", 5), graph_size // 8))),
            "beam_width": min(10, max(4, max(_int_setting("route_beam_width", 6), graph_size // 12))),
            "branch_limit": min(12, max(4, max(_int_setting("route_branch_limit", 8), graph_size // 10))),
        }

    def _rank_route_proposals(
        self,
        airport_id: str,
        budget_remaining: float,
        time_remaining_min: int,
        visited: Optional[Set[str]] = None,
        limit: Optional[int] = None,
    ) -> List[RouteProposal]:
        """Rank nearby routes for the current airport using the route proposal score."""
        visited_set = set(visited or set())
        proposals: List[RouteProposal] = []

        for route in self.planner.graph.get_neighbors(airport_id):
            destination = getattr(route, "destination_vertex", None)
            if not destination or destination in visited_set:
                continue

            proposal = self._build_route_proposal(route, include_future=False)
            if proposal is None:
                continue

            if proposal.projected_budget_after_flight > budget_remaining and proposal.projected_time_remaining_after_flight > time_remaining_min:
                # keep the proposal; the full route planning layer may still decide to use it
                pass

            proposals.append(proposal)

        proposals.sort(
            key=lambda proposal: (
                -proposal.priority_score,
                proposal.projected_budget_after_flight,
                proposal.projected_time_remaining_after_flight,
                proposal.destination,
            )
        )

        if limit is not None and limit > 0:
            return proposals[:limit]
        return proposals

    def _resolved_aircraft_rates(self) -> Dict[str, Dict[str, float]]:
        """Merge default and overridden aircraft rates into a normalized lookup table."""
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

    def _cheapest_route_option(self, route: Any) -> Optional[Dict[str, Any]]:
        """Pick the lowest-cost and fastest valid aircraft option for a route."""
        route_is_subsidized = float(getattr(route, "cost", 0.0)) == 0.0
        rates = self._resolved_aircraft_rates()
        best_option: Optional[Dict[str, Any]] = None

        for aircraft in getattr(route, "aircrafts", []):
            aircraft_key = AIRCRAFT_NAME_MAP.get(aircraft, aircraft)
            aircraft_rates = rates.get(aircraft_key)
            if not aircraft_rates:
                continue

            cost_usd = 0.0 if route_is_subsidized else round(float(route.distance) * float(aircraft_rates.get("cost_per_km", 0.0)), 2)
            time_min = int(round(float(route.distance) * float(aircraft_rates.get("time_per_km_min", 0.0))))
            candidate = {
                "aircraft": aircraft,
                "aircraft_key": aircraft_key,
                "cost_usd": cost_usd,
                "time_min": time_min,
                "is_subsidized": route_is_subsidized,
            }

            if best_option is None:
                best_option = candidate
                continue

            current_key = (float(candidate["cost_usd"]), int(candidate["time_min"]))
            best_key = (float(best_option["cost_usd"]), int(best_option["time_min"]))
            if current_key < best_key:
                best_option = candidate

        return best_option

    def _airport_coverage_potential(self, airport_id: str) -> float:
        """Estimate how much future coverage an airport can unlock."""
        cache = getattr(self, "_coverage_potential_cache", None)
        if not isinstance(cache, dict):
            cache = {}

        if airport_id in cache:
            return float(cache[airport_id])

        airport = self.planner.graph.get_vertex(airport_id)
        if airport is None:
            cache[airport_id] = 0.0
            self._coverage_potential_cache = cache
            return 0.0

        neighbors = self.planner.graph.get_neighbors(airport_id)
        direct_degree = len(neighbors)
        second_hop_degree = 0
        seen_second_hop: Set[str] = set()

        for route in neighbors:
            destination = getattr(route, "destination_vertex", None)
            if not destination:
                continue
            for second_route in self.planner.graph.get_neighbors(destination):
                second_destination = getattr(second_route, "destination_vertex", None)
                if second_destination and second_destination != airport_id and second_destination not in seen_second_hop:
                    seen_second_hop.add(second_destination)
                    second_hop_degree += 1

        hub_bonus = 3.0 if getattr(airport, "is_hub", False) else 0.0
        score = float(direct_degree * 4 + second_hop_degree * 2) + hub_bonus
        cache[airport_id] = score
        self._coverage_potential_cache = cache
        return score

    def _dijkstra_shortest_paths(self, origin: str) -> Tuple[Dict[str, float], Dict[str, Tuple[Optional[str], str, str, float, int, bool]]]:
        """Compute shortest paths from an origin airport using route cost as weight."""
        all_ids = [v.airport_id for v in self.planner.graph.vertices]
        dist = {airport_id: float("inf") for airport_id in all_ids}
        pred: Dict[str, Tuple[Optional[str], str, str, float, int, bool]] = {
            airport_id: (None, "", "", float("inf"), 0, False) for airport_id in all_ids
        }
        unvisited = set(all_ids)

        dist[origin] = 0.0

        while unvisited:
            current = min(unvisited, key=lambda airport_id: dist[airport_id])
            if dist[current] == float("inf"):
                break

            unvisited.remove(current)
            for route in self.planner.graph.get_neighbors(current):
                destination = getattr(route, "destination_vertex", None)
                if not destination or destination not in unvisited:
                    continue

                best_option = self._cheapest_route_option(route)
                if best_option is None:
                    continue

                candidate_dist = dist[current] + float(best_option["cost_usd"])
                if candidate_dist < dist[destination]:
                    dist[destination] = candidate_dist
                    pred[destination] = (
                        current,
                        str(best_option["aircraft"]),
                        str(best_option["aircraft_key"]),
                        float(best_option["cost_usd"]),
                        int(best_option["time_min"]),
                        bool(best_option["is_subsidized"]),
                    )

        return dist, pred

    def _reconstruct_path(self, origin: str, destination: str, pred: Dict[str, Tuple[Optional[str], str, str, float, int, bool]]) -> List[str]:
        """Rebuild a path from the Dijkstra predecessor table."""
        path: List[str] = []
        current = destination

        while current is not None:
            path.insert(0, current)
            if current == origin:
                break
            prev = pred.get(current, (None, "", "", 0.0, 0, False))[0]
            current = prev

        if not path or path[0] != origin:
            return []
        return path

    def calculate_tramo(self, distance_km: float, tipo_aeronave: str, es_subsidiada: bool) -> Dict[str, Any]:
        """Calculate the cost and time for a flight segment and validate subsidy limits."""
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

    def _build_coverage_route_plan(self, origin: str) -> List[Dict[str, Any]]:
        """Build a multi-step route plan that prioritizes destination coverage."""
        all_airports = [airport.airport_id for airport in self.planner.graph.vertices]
        if origin not in all_airports:
            return []

        planning_settings = self._planning_settings()
        beam_width = min(16, max(6, planning_settings["beam_width"] * 2))
        branch_limit = min(8, max(4, planning_settings["branch_limit"]))
        max_iterations = max(1, len(all_airports) * 2)

        frontier: List[Dict[str, Any]] = [
            {
                "current": origin,
                "visited": {origin},
                "path": [],
                "score": 0.0,
                "cost": 0.0,
            }
        ]

        for _ in range(max_iterations):
            next_frontier: List[Dict[str, Any]] = []

            for node in frontier:
                current_airport = node["current"]
                visited = set(node["visited"])

                if len(visited) >= len(all_airports):
                    next_frontier.append(node)
                    continue

                dist, pred = self._dijkstra_shortest_paths(current_airport)
                candidates: List[Tuple[float, float, int, str, List[str], float]] = []

                for airport_id in all_airports:
                    if airport_id in visited or airport_id == current_airport:
                        continue
                    if dist.get(airport_id, float("inf")) == float("inf"):
                        continue

                    path = self._reconstruct_path(current_airport, airport_id, pred)
                    if len(path) < 2:
                        continue

                    new_nodes = [node_id for node_id in path if node_id not in visited]
                    if not new_nodes:
                        continue

                    path_cost = float(dist[airport_id])
                    coverage_potential = self._airport_coverage_potential(airport_id)
                    score = (len(new_nodes) * 1000.0) + (coverage_potential * 100.0) - path_cost
                    candidates.append((score, path_cost, len(new_nodes), airport_id, path, coverage_potential))

                if not candidates:
                    next_frontier.append(node)
                    continue

                candidates.sort(key=lambda item: (-item[0], item[1], -item[2], item[3]))

                for candidate_score, path_cost, _, chosen_destination, chosen_path, coverage_potential in candidates[:branch_limit]:
                    expanded_steps: List[Dict[str, Any]] = []
                    for hop_index in range(1, len(chosen_path)):
                        previous_airport = chosen_path[hop_index - 1]
                        next_airport = chosen_path[hop_index]
                        route = next(
                            (
                                candidate_route
                                for candidate_route in self.planner.graph.get_neighbors(previous_airport)
                                if candidate_route.destination_vertex == next_airport
                            ),
                            None,
                        )
                        if route is None:
                            continue

                        best_option = self._cheapest_route_option(route)
                        if best_option is None:
                            continue

                        expanded_steps.append(
                            {
                                "step": len(node["path"]) + len(expanded_steps) + 1,
                                "origin": previous_airport,
                                "destination": next_airport,
                                "route_id": f"{previous_airport}->{next_airport}",
                                "distance_km": float(route.distance),
                                "minimum_stay_min": int(getattr(route, "minimum_stay", 0) or 0),
                                "transport_option": {
                                    "aircraft": best_option["aircraft"],
                                    "cost_usd": best_option["cost_usd"],
                                    "time_min": best_option["time_min"],
                                    "is_subsidized": best_option["is_subsidized"],
                                },
                                "priority_score": round(candidate_score, 2),
                                "reachable_destinations": int(coverage_potential),
                                "selection_reason": f"Cobertura Dijkstra desde {previous_airport} hacia {chosen_destination}",
                            }
                        )

                    if not expanded_steps:
                        continue

                    new_visited = visited | set(chosen_path)
                    next_frontier.append(
                        {
                            "current": chosen_destination,
                            "visited": new_visited,
                            "path": node["path"] + expanded_steps,
                            "score": float(node["score"]) + float(candidate_score),
                            "cost": float(node["cost"]) + float(path_cost),
                        }
                    )

            if not next_frontier:
                break

            next_frontier.sort(
                key=lambda item: (
                    -len(item["visited"]),
                    -item["score"],
                    item["cost"],
                    len(item["path"]),
                    item["current"],
                )
            )
            frontier = next_frontier[:beam_width]

        if not frontier:
            return []

        frontier.sort(
            key=lambda item: (
                -len(item["visited"]),
                -item["score"],
                item["cost"],
                len(item["path"]),
                item["current"],
            )
        )
        return frontier[0]["path"]

    def _best_job_income(self, airport: Any) -> float:
        """Return the best possible income from the jobs available at an airport."""
        best_income = 0.0
        for job in getattr(airport, "jobs", []):
            hourly_rate = float(getattr(job, "hourly_rate", 0.0))
            max_hours = float(getattr(job, "max_hours", 0.0))
            best_income = max(best_income, round(hourly_rate * max_hours, 2))
        return round(best_income, 2)

    def _best_route_option(self, route: Any, budget_remaining: float, time_remaining_min: int) -> Optional[Dict[str, Any]]:
        """Select the best transport option that still fits the remaining budget and time."""
        route_is_subsidized = float(getattr(route, "cost", 0.0)) == 0.0
        best_calc: Optional[Dict[str, Any]] = None

        for aircraft in getattr(route, "aircrafts", []):
            calc = self.calculate_tramo(route.distance, aircraft, route_is_subsidized)
            if not calc.get("ok"):
                continue
            if float(calc["cost_usd"]) > float(budget_remaining):
                continue
            if int(calc["time_min"]) > int(time_remaining_min):
                continue

            if best_calc is None:
                best_calc = calc
                continue

            current_key = (float(calc["cost_usd"]), int(calc["time_min"]))
            best_key = (float(best_calc["cost_usd"]), int(best_calc["time_min"]))
            if current_key < best_key:
                best_calc = calc

        return best_calc

    def _future_reachability_score(
        self,
        airport_id: str,
        budget_remaining: float,
        time_remaining_min: int,
        depth: int,
        visited: Optional[Set[str]] = None,
        branch_limit: Optional[int] = None,
    ) -> Tuple[int, float]:
        """Estimate how many future destinations remain reachable from an airport."""
        if depth <= 0:
            return 0, 0.0

        airport = self.planner.graph.get_vertex(airport_id)
        if airport is None:
            return 0, 0.0

        visited = set(visited or set())
        visited.add(airport_id)

        effective_budget = float(budget_remaining)
        threshold_budget = float(self.state.budget_initial) * float(getattr(self.config, "budget_threshold_pct", 0.35))
        if effective_budget < threshold_budget:
            effective_budget += self._best_job_income(airport)

        best_count = 0
        best_cost = 0.0

        ranked_routes = self._rank_route_proposals(
            airport_id,
            effective_budget,
            time_remaining_min,
            visited=visited,
            limit=branch_limit,
        )

        for proposal in ranked_routes:
            best_option = proposal.transport_options[0] if proposal.transport_options else None
            if best_option is None:
                continue

            next_budget = effective_budget - float(best_option.cost_usd)
            next_time = int(time_remaining_min) - int(best_option.time_min)
            if next_budget < 0 or next_time < 0:
                continue

            destination = proposal.destination
            if next_budget < threshold_budget:
                destination_airport = self.planner.graph.get_vertex(destination)
                if destination_airport is not None:
                    next_budget += self._best_job_income(destination_airport)

            sub_count, sub_cost = self._future_reachability_score(
                destination,
                next_budget,
                next_time,
                depth - 1,
                visited,
                branch_limit=branch_limit,
            )

            candidate_count = 1 + sub_count
            candidate_cost = float(best_option.cost_usd) + sub_cost

            if candidate_count > best_count or (candidate_count == best_count and candidate_cost < best_cost):
                best_count = candidate_count
                best_cost = candidate_cost

        return best_count, round(best_cost, 2)

    def _build_route_proposal(self, route: Any, *, include_future: bool = True) -> Optional[RouteProposal]:
        """Turn a raw graph edge into a scored route proposal for the UI."""
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
            return None

        destination_airport = self.planner.graph.get_vertex(route.destination_vertex)
        threshold_budget = float(self.state.budget_initial) * float(getattr(self.config, "budget_threshold_pct", 0.35))
        best_option = min(options, key=lambda opt: (opt.cost_usd, opt.time_min))
        projected_budget = max(0.0, float(self.state.budget_remaining) - float(best_option.cost_usd))
        projected_time = max(0, int(self.state.time_remaining_min) - int(best_option.time_min))

        if projected_budget < threshold_budget and destination_airport is not None:
            projected_budget += self._best_job_income(destination_airport)

        planning_settings = self._planning_settings()

        if include_future:
            reachable_destinations, future_cost = self._future_reachability_score(
                route.destination_vertex,
                projected_budget,
                projected_time,
                depth=planning_settings["lookahead_depth"],
                visited={self.state.current_airport},
                branch_limit=planning_settings["branch_limit"],
            )
        else:
            reachable_destinations, future_cost = 0, 0.0

        minimum_stay_min = int(getattr(route, "minimum_stay", 0) or 0)
        estimated_job_income = self._best_job_income(destination_airport) if destination_airport is not None else 0.0
        # Prefer routes that unlock more destinations, then cheaper/faster ones.
        priority_score = (
            reachable_destinations * 1000.0
            + estimated_job_income
            - (future_cost + float(best_option.cost_usd))
            - (float(best_option.time_min) * 0.5)
            + (20.0 if route_is_subsidized else 0.0)
        )

        if not include_future:
            priority_score = (
                estimated_job_income
                - float(best_option.cost_usd)
                - (float(best_option.time_min) * 0.5)
                + (20.0 if route_is_subsidized else 0.0)
            )

        selection_reason = (
            f"{reachable_destinations} destinos alcanzables"
            f" · costo proyectado ${future_cost + float(best_option.cost_usd):.2f}"
            f" · ingreso potencial ${estimated_job_income:.2f}"
        )

        return RouteProposal(
            id=f"{self.state.current_airport}->{route.destination_vertex}",
            origin=self.state.current_airport,
            destination=route.destination_vertex,
            distance_km=float(route.distance),
            transport_options=sorted(options, key=lambda opt: (opt.cost_usd, opt.time_min)),
            est_arrival_min=self.state.time_elapsed_min + min(o.time_min for o in options),
            minimum_stay_min=minimum_stay_min,
            reachable_destinations=reachable_destinations,
            projected_budget_after_flight=round(projected_budget, 2),
            projected_time_remaining_after_flight=projected_time,
            estimated_job_income=round(estimated_job_income, 2),
            priority_score=round(priority_score, 2),
            selection_reason=selection_reason,
            blocked=bool(getattr(route, "blocked", False)),
        )

    def _plan_from_state(self, simulated_state: Any, max_steps: int = 6) -> List[Dict[str, Any]]:
        """Generate a coverage-oriented plan from the current simulated airport."""
        return self._build_coverage_route_plan(simulated_state.current_airport)

    def _serialize_route_suggestion(self, proposal: RouteProposal) -> Dict[str, Any]:
        """Convert a route proposal into a JSON-friendly suggestion payload."""
        return {
            "id": proposal.id,
            "destination": proposal.destination,
            "distance_km": proposal.distance_km,
            "minimum_stay_min": proposal.minimum_stay_min,
            "reachable_destinations": proposal.reachable_destinations,
            "projected_budget_after_flight": proposal.projected_budget_after_flight,
            "projected_time_remaining_after_flight": proposal.projected_time_remaining_after_flight,
            "estimated_job_income": proposal.estimated_job_income,
            "priority_score": proposal.priority_score,
            "selection_reason": proposal.selection_reason,
            "origin": proposal.origin,
            "blocked": proposal.blocked,
            "transport_options": [
                {
                    "aircraft": option.aircraft,
                    "cost_usd": option.cost_usd,
                    "time_min": option.time_min,
                    "is_subsidized": option.is_subsidized,
                }
                for option in proposal.transport_options
            ],
        }

    def suggest_route(self) -> Dict[str, Any]:
        """Choose the best current route and persist the planned path in session state."""
        proposals = self.step_proposals()
        suggested = next((route for route in proposals.routes if not bool(getattr(route, "blocked", False))), None)
        settings = self._planning_settings()
        route_plan = self._plan_from_state(deepcopy(self.state), max_steps=settings["max_steps"])

        if suggested is None:
            self.state.last_suggested_route = None
            self.state.planned_route = []
            return {
                "suggested_route": None,
                "route_plan": [],
                "proposals": proposals,
            }

        suggestion = self._serialize_route_suggestion(suggested)
        self.state.last_suggested_route = suggestion
        self.state.planned_route = list(route_plan)

        return {
            "suggested_route": suggestion,
            "route_plan": route_plan,
            "proposals": proposals,
        }

    def step_proposals(self) -> StepProposalResult:
        """Build the available routes, activities, jobs, and mandatory actions for the step."""
        routes: List[RouteProposal] = []
        activities: List[Any] = []
        jobs: List[Any] = []

        current_airport = self.planner.graph.get_vertex(self.state.current_airport)
        if current_airport is not None:
            activities = list(getattr(current_airport, "activities", []))
            jobs = list(getattr(current_airport, "jobs", []))

        for route in self.planner.graph.get_neighbors(self.state.current_airport):
            proposal = self._build_route_proposal(route)
            if proposal is None:
                continue
            routes.append(proposal)

        routes.sort(key=lambda proposal: (-proposal.priority_score, proposal.projected_budget_after_flight, proposal.projected_time_remaining_after_flight))

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
                "free_time_min": self.state.free_time_min,
                "current_stay_required_min": self.state.current_stay_required_min,
                "current_optional_stay_min": self.state.current_optional_stay_min,
                "last_suggested_route": self.state.last_suggested_route,
                "planned_route": self.state.planned_route,
                "meal_accumulated_min": self.state.meal_accumulated_min,
                "lodging_accumulated_min": self.state.lodging_accumulated_min,
                "lodging_pending_after_flight": self.state.lodging_pending_after_flight,
            },
        )