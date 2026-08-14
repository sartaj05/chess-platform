from __future__ import annotations

import logging
import re
import time
import uuid

from django.conf import settings

logger = logging.getLogger("chess_platform.performance")


class RequestTelemetryMiddleware:
    """Attach request correlation and timing without collecting user content."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        candidate = request.headers.get("X-Request-ID", "")[:64]
        request_id = (
            candidate
            if candidate and re.fullmatch(r"[A-Za-z0-9._-]+", candidate)
            else uuid.uuid4().hex
        )
        request.request_id = request_id
        started = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - started) * 1000
        response["X-Request-ID"] = request_id
        response["Server-Timing"] = f'app;dur={duration_ms:.1f}'
        threshold = getattr(settings, "SLOW_REQUEST_THRESHOLD_MS", 750)
        if duration_ms >= threshold:
            logger.warning(
                "slow_request method=%s path=%s status=%s duration_ms=%.1f request_id=%s",
                request.method,
                request.path,
                response.status_code,
                duration_ms,
                request_id,
            )
        return response
