"""
Custom middleware for the FastAPI application
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses"""
    async def dispatch(self, request: Request, call_next):
        print(f"REQUEST: {request.method} {request.url.path}")
        response = await call_next(request)
        print(f"RESPONSE: {response.status_code}")
        return response
