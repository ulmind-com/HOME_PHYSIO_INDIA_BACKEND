"""Great-circle distance helpers for location-based therapist matching."""

from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt

#: Mean radius of the Earth, in kilometres (IUGG value).
EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two lat/lng points, in kilometres.

    Good enough for ranking nearby therapists — road distance will differ,
    but the ordering it produces is what an "as the crow flies" match needs.
    """
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lng2 - lng1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(a), sqrt(1 - a))
