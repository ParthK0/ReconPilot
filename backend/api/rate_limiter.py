"""
backend/api/rate_limiter.py
===========================
In-memory sliding window rate limiting middleware for ReconPilot API.
"""

import time
from collections import defaultdict
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests_map: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Exclude health checks from rate limiting
        if request.url.path in ("/health", "/api/v1/health", "/docs", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old timestamps
        recent_requests = [ts for ts in self.requests_map[client_ip] if ts > window_start]
        recent_requests.append(now)
        self.requests_map[client_ip] = recent_requests

        if len(recent_requests) > self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Maximum allowed is 120 requests per minute.",
                    "retry_after_seconds": int(self.window_seconds - (now - recent_requests[0])),
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        response = await call_next(request)
        return response
