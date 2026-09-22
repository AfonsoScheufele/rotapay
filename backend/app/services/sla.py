
from __future__ import annotations

import math

from app.core.config import get_settings

EARTH_RADIUS_KM = 6371.0

def haversine_km(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))

def estimate_sla_hours(distance_km: float) -> int:
    settings = get_settings()
    avg = max(settings.sla_avg_kmh, 1.0)
    raw = (distance_km / avg) * settings.sla_buffer
    hours = int(math.ceil(raw))
    return max(settings.sla_min_hours, min(settings.sla_max_hours, hours))

def estimate_sla_hours_for_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> tuple[float, int]:
    km = haversine_km(origin_lat, origin_lng, dest_lat, dest_lng)
    return km, estimate_sla_hours(km)
