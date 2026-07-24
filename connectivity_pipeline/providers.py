from __future__ import annotations

import re
from typing import Any


def normalize_provider_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "Unknown"

    lowered = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    aliases = {
        "airtel": "Airtel",
        "airtel india": "Airtel",
        "bharti airtel": "Airtel",
        "bharti airtel ltd": "Airtel",
        "bharti": "Airtel",
        "jio": "Jio",
        "reliance jio": "Jio",
        "reliance jio infocomm": "Jio",
        "vodafone idea": "Vodafone Idea",
        "vodafone idea limited": "Vodafone Idea",
        "vodafone idea ltd": "Vodafone Idea",
        "vi limited": "Vodafone Idea",
        "vi": "Vodafone Idea",
        "vodafone": "Vodafone Idea",
        "vodafone india": "Vodafone Idea",
        "vodafone cellular": "Vodafone Idea",
        "vodafone essar": "Vodafone Idea",
        "idea": "Vodafone Idea",
        "idea cellular": "Vodafone Idea",
        "idea cellular ltd": "Vodafone Idea",
        "bsnl": "BSNL",
        "bharat sanchar nigam limited": "BSNL",
        "mtnl": "MTNL",
        "reliance communications": "Reliance Communications",
        "rcil": "Reliance Communications",
        "aircel": "Aircel",
        "aircel cellular": "Aircel",
        "tata docomo": "Tata Docomo",
        "tata docomo internet services": "Tata Docomo",
        "tata indicom": "Tata Docomo",
        "tata teleservices": "Tata Docomo",
        "docomo": "Tata Docomo",
        "uninor": "Uninor",
        "telenor": "Telenor",
        "videocon": "Videocon",
        "loop mobile": "Loop Mobile",
        "mts": "MTS",
    }
    return aliases.get(lowered, text.strip())


def provider_from_codes(mcc: Any, mnc: Any, operator_name: Any, mapping: dict[str, str]) -> str:
    key = f"{str(mcc or '').strip()}-{str(mnc or '').strip()}"
    if key in mapping:
        return mapping[key]

    normalized = normalize_provider_name(operator_name)
    if normalized != "Unknown":
        return normalized

    return "Unknown"
