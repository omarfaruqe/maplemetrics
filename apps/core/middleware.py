"""Request logging: one line per request, with a request id and how long it took."""

from __future__ import annotations

import logging
import re
import time
import uuid

from .logs import request_id_var

logger = logging.getLogger("maplemetrics.request")

# An id sent by a proxy is trusted only if it is short and made of harmless characters, so a client
# cannot inject odd text into the logs.
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestLogMiddleware:
    """Gives each request an id, times it and logs the outcome.

    Healthcheck calls come every few seconds, so they are logged at DEBUG to keep real traffic
    visible.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex
        request.request_id = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = self.get_response(request)
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            level = logging.ERROR if response.status_code >= 500 else logging.INFO
            if request.path_info == "/health/":
                level = logging.DEBUG
            logger.log(
                level,
                "%s %s %s",
                request.method,
                request.path,
                response.status_code,
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            response["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token)
