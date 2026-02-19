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
from server.core.database import init_db
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


@app.on_event("startup")
async def startup_event():
    """Initialize database on server startup - creates tables if they don't exist"""
    import os
    from server.core.config import DATABASE_DIR
    
    # Ensure data directory exists
    os.makedirs(DATABASE_DIR, exist_ok=True)
    
    # Initialize database (creates tables if they don't exist)
    init_db()
    print("✓ Database initialized")

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
    import sys
    import os
    import uvicorn
    
    # Add project root to Python path if running directly
    if __file__:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
    
    print("=" * 50)
    print("Starting Essay Testing System Server...")
    print("=" * 50)
    print(f"Server will be available at: http://localhost:8000")
    print(f"API docs available at: http://localhost:8000/docs")
    print("=" * 50)
    print("Press CTRL+C to stop the server")
    print("=" * 50)
    # Run on 0.0.0.0 to allow network access from other devices
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
