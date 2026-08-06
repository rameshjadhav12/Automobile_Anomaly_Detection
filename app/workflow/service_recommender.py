"""Deterministic 'tool' that selects a service recommendation given diagnostic code metadata.

This is implemented as a plain rule-based function rather than an LLM call, matching the
"tool-like workflow for service recommendation selection" requirement: severity/urgency
decisions for a service center should be deterministic and auditable, not left to
generative text.
"""
from __future__ import annotations

SEVERITY_RECOMMENDATIONS: dict[str, dict[str, str]] = {
    "Critical": {
        "urgency": "Critical",
        "timeframe": "Immediate - do not drive",
        "action": (
            "Advise the customer not to drive the vehicle. Schedule an immediate service "
            "appointment or arrange a tow-in. This condition poses a safety risk."
        ),
    },
    "High": {
        "urgency": "High",
        "timeframe": "Within 1-2 days",
        "action": (
            "Schedule a service appointment within the next 1-2 days to prevent further "
            "component damage or drivability issues."
        ),
    },
    "Medium": {
        "urgency": "Medium",
        "timeframe": "Within 1-2 weeks",
        "action": "Schedule a service appointment within the next 1-2 weeks.",
    },
    "Low": {
        "urgency": "Low",
        "timeframe": "Next routine maintenance",
        "action": "No urgent action required; address at the next scheduled maintenance visit.",
    },
}

DEFAULT_RECOMMENDATION = {
    "urgency": "Unknown",
    "timeframe": "Recommend general inspection",
    "action": (
        "Severity could not be determined from available data. Recommend a general "
        "diagnostic inspection to confirm the issue before scheduling further service."
    ),
}


def recommend_service_action(code_metadata: dict | None) -> dict:
    """Return a deterministic service recommendation for the given diagnostic code metadata.

    Args:
        code_metadata: dict with at least a "severity" key (from data/diagnostic_codes.json),
            or None if no diagnostic code could be matched.
    """
    if not code_metadata:
        return dict(DEFAULT_RECOMMENDATION)

    severity = code_metadata.get("severity", "")
    recommendation = SEVERITY_RECOMMENDATIONS.get(severity, DEFAULT_RECOMMENDATION)
    result = dict(recommendation)
    result["code"] = code_metadata.get("code", "")
    result["system"] = code_metadata.get("system", "")
    return result
