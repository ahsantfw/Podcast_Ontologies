"""
FastAPI logging setup with request-scoped IDs.
"""

import uuid
from typing import Callable

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from core_engine.logging import load_logging_config, get_logger, with_context


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        workspace_id = request.headers.get("x-workspace-id")
        logger = get_logger("backend", request_id=request_id, workspace_id=workspace_id)
        request.state.logger = logger
        request.state.request_id = request_id
        request.state.workspace_id = workspace_id

        logger.info("request_start", extra={"context": {"path": request.url.path, "method": request.method}})
        try:
            response = await call_next(request)
            logger.info("request_end", extra={"context": {"status_code": response.status_code}})
            response.headers["x-request-id"] = request_id
            return response
        except Exception as exc:  # noqa: BLE001
            logger.error("request_error", exc_info=True)
            raise


def setup_logging(app: FastAPI):
    """
    Initialize logging and add request logging middleware.
    Call once at app startup.
    """
    load_logging_config()
    app.add_middleware(RequestLoggingMiddleware)

