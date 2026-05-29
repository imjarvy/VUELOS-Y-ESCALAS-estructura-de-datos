from typing import Dict, Any

# Global configuration defaults used by the planner and UI.
# These values can be overridden through the configuration panel.
GRAPH_CONFIG_DEFAULTS: Dict[str, Any] = {
    "aeronaves": {
        "commercial": {"costoKm": 0.18, "tiempoKm": 0.7},
        "regional": {"costoKm": 0.25, "tiempoKm": 1.1},
        "propeller": {"costoKm": 0.12, "tiempoKm": 2.5},
    },
    "presupuestoMinimoPorc": 35.0,
    "intervaloAlojamiento": 20.0,
    "intervaloAlimentacion": 8.0,
}

# Backward-compatible aliases used by the current optimizers.
AIRCRAFT_RATES: Dict[str, Dict[str, float]] = {
    key: {
        "cost_per_km": value["costoKm"],
        "time_per_km_min": value["tiempoKm"],
    }
    for key, value in GRAPH_CONFIG_DEFAULTS["aeronaves"].items()
}

DEFAULTS: Dict[str, float] = {
    "budget_threshold_pct": GRAPH_CONFIG_DEFAULTS["presupuestoMinimoPorc"],
    "lodging_interval_h": GRAPH_CONFIG_DEFAULTS["intervaloAlojamiento"],
    "meal_interval_h": GRAPH_CONFIG_DEFAULTS["intervaloAlimentacion"],
    "max_subsidized_distance_frac": 0.20,
    "route_plan_max_steps": 12,
    "route_lookahead_depth": 5,
    "route_beam_width": 6,
    "route_branch_limit": 8,
}


__all__ = ["GRAPH_CONFIG_DEFAULTS", "AIRCRAFT_RATES", "DEFAULTS"]

