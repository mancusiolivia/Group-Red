#!/usr/bin/env python3
"""
Simple script to run the server
Just run: python3 run_server.py
"""
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    import uvicorn
    from server.main import app
    
    print("=" * 50)
    print("Starting Essay Testing System Server...")
    print("=" * 50)
    print(f"Server will be available at: http://localhost:8000")
    print(f"API docs available at: http://localhost:8000/docs")
    print("=" * 50)
    print("Press CTRL+C to stop the server")
    print("=" * 50)
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
