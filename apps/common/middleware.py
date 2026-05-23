import logging
import time
import uuid

from apps.common.request_context import reset_request_id, set_request_id

logger = logging.getLogger("apps.common.request")


class RequestIDMiddleware:
    header_name = "HTTP_X_REQUEST_ID"
    response_header = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming_request_id = request.META.get(self.header_name)
        request_id = incoming_request_id or str(uuid.uuid4())
        request.request_id = request_id
        token = set_request_id(request_id)

        started_at = time.perf_counter()
        try:
            response = self.get_response(request)
        finally:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            user = getattr(request, "user", None)
            user_id = user.id if getattr(user, "is_authenticated", False) else None
            logger.info(
                "request_complete method=%s path=%s status=%s duration_ms=%.2f user_id=%s",
                request.method,
                request.path,
                getattr(response, "status_code", "unknown") if "response" in locals() else "error",
                elapsed_ms,
                user_id,
            )
            reset_request_id(token)

        response[self.response_header] = request_id
        return response
