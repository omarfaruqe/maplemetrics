from django.conf import settings
from rest_framework.throttling import AnonRateThrottle


class AnonymousRateThrottle(AnonRateThrottle):
    """Per-client request limit for the public API, from API_THROTTLE_RATE such as 120/min."""

    def get_rate(self) -> str:
        return settings.API_THROTTLE_RATE
