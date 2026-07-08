from typing import Dict, Any

# Rough $/kWh used only to give a directional cost impact figure in the demo.
COST_PER_KWH = 0.15


def simulate_scenario(baseline_kwh: float, scenario_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Simple, explainable simulation model. Each scenario type applies a
    parameterized multiplier/delta to the baseline consumption so users can see
    directional impact rather than a black-box number."""
    projected = baseline_kwh

    if scenario_type == "occupancy":
        # parameters: occupancy_change_percent (e.g. +20 or -30)
        change_pct = parameters.get("occupancy_change_percent", 0)
        # Assume energy scales at ~0.6x the occupancy change (partial correlation)
        projected = baseline_kwh * (1 + (change_pct / 100) * 0.6)

    elif scenario_type == "temperature":
        # parameters: temperature_change_c
        delta_t = parameters.get("temperature_change_c", 0)
        # Assume ~3% energy change per degree C (HVAC load sensitivity)
        projected = baseline_kwh * (1 + delta_t * 0.03)

    elif scenario_type == "shutdown":
        # parameters: hours_shutdown_per_day, device_share_of_load (0-1)
        hours = parameters.get("hours_shutdown_per_day", 0)
        device_share = parameters.get("device_share_of_load", 0.2)
        reduction_fraction = min(hours / 24, 1.0) * device_share
        projected = baseline_kwh * (1 - reduction_fraction)

    elif scenario_type == "peak_reduction":
        # parameters: peak_reduction_percent
        reduction_pct = parameters.get("peak_reduction_percent", 0)
        # Peak hours assumed to represent ~35% of daily consumption
        projected = baseline_kwh * (1 - (reduction_pct / 100) * 0.35)

    else:
        raise ValueError(f"Unknown scenario_type: {scenario_type}")

    savings_kwh = round(baseline_kwh - projected, 3)
    savings_percent = round((savings_kwh / baseline_kwh) * 100, 2) if baseline_kwh else 0.0
    cost_impact = round(savings_kwh * COST_PER_KWH, 2)

    return {
        "baseline_kwh": round(baseline_kwh, 3),
        "projected_kwh": round(projected, 3),
        "savings_kwh": savings_kwh,
        "savings_percent": savings_percent,
        "estimated_cost_impact": cost_impact,
    }
