from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, List


AIRCRAFT_NAME_MAP: Dict[str, str] = {
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


def normalize_aircraft_name(name: str) -> str:
    return AIRCRAFT_NAME_MAP.get(name, name)


def serialize_item(item: Any) -> Any:
    if hasattr(item, "to_dict"):
        return item.to_dict()
    if is_dataclass(item):
        return asdict(item)
    return item


def build_visited_from_legs(legs: Iterable[Any]) -> List[Dict[str, Any]]:
    visited: List[Dict[str, Any]] = []
    legs_list = list(legs)
    if not legs_list:
        return visited

    first_origin = getattr(legs_list[0], "origin_id", None)
    if first_origin:
        visited.append({"airport_id": first_origin})

    for leg in legs_list:
        destination_id = getattr(leg, "destination_id", None)
        if destination_id and (not visited or visited[-1]["airport_id"] != destination_id):
            visited.append({"airport_id": destination_id})

    return visited


def total_gained_from_jobs(jobs: Iterable[Any]) -> float:
    return round(
        sum(float(job.get("income_usd", 0.0)) for job in jobs if isinstance(job, dict)),
        2,
    )