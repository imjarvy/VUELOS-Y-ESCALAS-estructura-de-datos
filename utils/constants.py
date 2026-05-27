from typing import Dict

# Rates and timings by aircraft type.
# cost_per_km: USD per kilometer
# time_per_km_min: minutes per kilometer (flight duration factor)
AIRCRAFT_RATES: Dict[str, Dict[str, float]] = {
    "commercial": {"cost_per_km": 0.18, "time_per_km_min": 0.7},
    "regional": {"cost_per_km": 0.25, "time_per_km_min": 1.1},
    "propeller": {"cost_per_km": 0.12, "time_per_km_min": 2.5},
}


# Global defaults (can be overridden from JSON configuration)
DEFAULTS: Dict[str, float] = {
    # Percent of initial budget that enables job offers
    "budget_threshold_pct": 35.0,
    # Mandatory intervals (hours)
    "lodging_interval_h": 20.0,
    "meal_interval_h": 8.0,
    # Max fraction of total trip distance that can be subsidized (20% = 0.20)
    "max_subsidized_distance_frac": 0.20,
}


__all__ = ["AIRCRAFT_RATES", "DEFAULTS"]
