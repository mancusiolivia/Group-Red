"""
Custom middleware for the FastAPI application
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses"""
    async def dispatch(self, request: Request, call_next):
        import sys
        print(f"REQUEST: {request.method} {request.url.path}", flush=True)
        sys.stdout.flush()
        try:
            response = await call_next(request)
            print(f"RESPONSE: {response.status_code}", flush=True)
            sys.stdout.flush()
            return response
        except Exception as e:
            print(f"ERROR in request: {type(e).__name__}: {str(e)}", flush=True)
            sys.stdout.flush()
            raise
