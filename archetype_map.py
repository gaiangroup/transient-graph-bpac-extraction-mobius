"""Episode type → BEv archetype mapping (Layer 3 motif types → Layer 5 semantics)."""

EPISODE_TO_ARCHETYPE = {
    "FRAUD_SEQUENCE":          "FRAUDULENT_COORDINATION",
    "COORDINATED_RATING":      "COORDINATED_MANIPULATION",
    "WASH_TRADING":            "CIRCULAR_VALUE_TRANSFER",
    "DATA_EXFILTRATION":       "UNAUTHORIZED_DATA_FLOW",
    "SENSOR_FAILURE_PATTERN":  "CASCADING_INFRASTRUCTURE_FAILURE",
    # fallback — unknown episode types land here
    "UNKNOWN":                 "ANOMALOUS_EVENT",
}


def episode_type_to_archetype(episode_type: str) -> str:
    return EPISODE_TO_ARCHETYPE.get(episode_type, EPISODE_TO_ARCHETYPE["UNKNOWN"])
