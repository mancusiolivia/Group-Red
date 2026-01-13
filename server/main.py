"""
FastAPI server for Essay Testing and Evaluation System
Handles question generation, student responses, and AI-powered grading

to run server: uvicorn server.main:app
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from server.core.config import CLIENT_STATIC_DIR
from server.core.middleware import LoggingMiddleware
from server.api import router as api_router
from server.frontend import router as frontend_router

# Create FastAPI app
app = FastAPI(
    title="Essay Testing System", 
    version="1.0.0", 
    docs_url="/docs", 
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(frontend_router)
app.include_router(api_router)

# Mount static files after routes are defined
app.mount("/static", StaticFiles(directory=CLIENT_STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Starting server...")
    print(f"Registered routes: {[route.path for route in app.routes]}")
    print(f"App instance: {app}")
    print(f"App title: {app.title}")
    print("=" * 50)
    # Run on 0.0.0.0 to allow network access from other devices
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
