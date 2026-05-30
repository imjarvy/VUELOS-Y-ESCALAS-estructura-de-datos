"""
services/report_generator.py

Assembles the final trip report for the REST API.
Purpose:
    Combines data from (Itinerary) and (TripReport) into one
    serializable dict.
    This is the final step before sending the response to the frontend.
    The report includes visited airports, legs, activities, jobs,
    Receives Graph, Itinerary and TripReport as parameters.

A traveler may use only basic
    planning  and never start an advanced session, or vice
    versa. The report must be useful in both scenarios.
"""

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

from core.graph import Graph
from models.itinerary import Itinerary
from models.planner_models import (
    ActivityRecord,
    DecisionRecord,
    JobRecord,
    TripReport,
)


# --------------------------------------------------------
# Internal serializers
# Handle objects or dicts depending on source step.

def _safe_dict(obj: Any) -> Dict[str, Any]:
    """Convert object to dict safely.
    Priority: to_dict → dataclass → dict → {}.
    """
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return obj
    return {}


def _serialize_visited(
    visited_raw: List[Dict[str, Any]],
    graph: Graph,
) -> List[Dict[str, Any]]:
    """Add airport info (name, city, country, timezone) from graph.
    Fallback: raw ID if airport not found.
    """
    result = []
    for entry in visited_raw:
        airport_id = entry.get("airport_id", "")
        airport = graph.get_vertex(airport_id)
        if airport:
            result.append({
                "airport_id":  airport.airport_id,
                "name":        airport.name,
                "city":        airport.city,
                "country":     airport.country,
                "timezone":    airport.timezone,
            })
        else:
            # Airport not in graph — include raw id so report is never empty
            result.append({"airport_id": airport_id, "name": airport_id,
                           "city": "", "country": "", "timezone": ""})
    return result


def _serialize_activities(activities: List[Any]) -> List[Dict[str, Any]]:
    """Serialize ActivityRecord objects or plain dicts.

    Output per item:
        name, type (mandatory/optional), duration_min, cost_usd,
        performed_at_min
    """
    result = []
    for record in activities:
        if isinstance(record, ActivityRecord):
            act = record.activity
            result.append({
                "name":            getattr(act, "name",         ""),
                "type":            getattr(act, "type",         ""),
                "duration_min":    getattr(act, "duration_min",  0),
                "cost_usd":        getattr(act, "cost_usd",     0.0),
                "performed_at_min": record.performed_at_min,
            })
        elif isinstance(record, dict):
            result.append(record)
        elif is_dataclass(record):
            result.append(asdict(record))
    return result


def _serialize_jobs(jobs: List[Any]) -> List[Dict[str, Any]]:
    """Serialize JobRecord objects or plain dicts.
    Output per item:
        name, hourly_rate, hours_worked, income_usd

    jobs may be stored as dicts in some
    sessions. Both formats are handled here.
    """
    result = []
    for record in jobs:
        if isinstance(record, JobRecord):
            job = record.job
            result.append({
                "name":         getattr(job, "name",         ""),
                "hourly_rate":  getattr(job, "hourly_rate",  0.0),
                "hours_worked": record.hours_worked,
                "income_usd":   record.income_usd,
            })
        elif isinstance(record, dict):
            result.append({
                "name":         record.get("name",        ""),
                "hourly_rate":  record.get("hourly_rate", 0.0),
                "hours_worked": record.get("hours_worked", 0),
                "income_usd":   record.get("income_usd",  0.0),
            })
        elif is_dataclass(record):
            result.append(asdict(record))
    return result


def _serialize_decisions(decisions: List[Any]) -> List[Dict[str, Any]]:
    """Serialize DecisionRecord or dict.
    Output: timestamp, kind, details.
    """
    result = []
    for d in decisions:
        if isinstance(d, DecisionRecord):
            result.append({
                "timestamp_min": d.timestamp_min,
                "kind":          d.kind,
                "details":       d.details,
            })
        elif isinstance(d, dict):
            result.append(d)
        elif is_dataclass(d):
            result.append(asdict(d))
    return result


# Public class                                                         #
# ------------------------------------------------------------------ #

class ReportGenerator:
    """Combine (Itinerary) and (TripReport) into final report."""

    def generate(
        self,
        graph: Graph,
        itinerary: Optional[Itinerary] = None,
        trip_report: Optional[TripReport] = None,
        decisions: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Build report dict.
        Keys: visited, legs, activities, jobs, decisions, totals.
        """

        # ── Visited airports ───
        if trip_report and trip_report.visited:
            visited = _serialize_visited(trip_report.visited, graph)
        elif itinerary:
            raw = [{"airport_id": aid} for aid in itinerary.visited_airports]
            visited = _serialize_visited(raw, graph)
        else:
            visited = []

        # ── Legs ───────────────
        if trip_report and trip_report.legs:
            legs = [_safe_dict(leg) for leg in trip_report.legs]
        elif itinerary:
            legs = [leg.to_dict() for leg in itinerary.legs]
        else:
            legs = []

        # ── Activities (R3 only) 
        activities = _serialize_activities(
            trip_report.activities if trip_report else []
        )

        # ── Jobs (R3 only) ──────
        jobs = _serialize_jobs(
            trip_report.jobs if trip_report else []
        )

        # ── Decisions (R3 only) ─
        serialized_decisions = _serialize_decisions(decisions or [])

        # ── Totals 
        if trip_report and trip_report.totals:

            totals = {
                "budget_initial":          trip_report.totals.get("budget_initial"),
                "total_spent":             trip_report.totals.get("total_spent"),
                "total_gained":            trip_report.totals.get("total_gained", 0.0),
                "final_balance":           trip_report.totals.get("final_balance"),
                "time_total_min":          trip_report.totals.get("time_total_min"),
                "distance_travelled_km":   trip_report.totals.get("distance_travelled_km"),
                "subsidized_distance_km":  trip_report.totals.get("subsidized_distance_km", 0.0),
            }
        elif itinerary:
            totals = {
                "budget_initial":         None,
                "total_spent":            round(itinerary.total_cost, 2),
                "total_gained":           0.0,
                "final_balance":          None,
                "time_total_min":         round(itinerary.total_time_min, 2),
                "distance_travelled_km":  round(
                    sum(leg.distance for leg in itinerary.legs), 2
                ),
                "subsidized_distance_km": 0.0,
            }
        else:
            totals = {}

        return {
            "visited":   visited,
            "legs":      legs,
            "activities": activities,
            "jobs":      jobs,
            "decisions": serialized_decisions,
            "totals":    totals,
        }