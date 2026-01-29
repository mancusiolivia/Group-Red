"""
Frontend serving for the Essay Testing System
Handles serving the HTML frontend and static files
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os

from server.core.config import CLIENT_HTML_DIR

router = APIRouter(tags=["frontend"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    """Serve the main frontend page"""
    print("=" * 50)
    print("ROOT ROUTE HIT!")
    print("=" * 50)
    html_path = os.path.join(CLIENT_HTML_DIR, "index.html")
    print(f"DEBUG: Serving root route. HTML path: {html_path}")
    print(f"DEBUG: File exists: {os.path.exists(html_path)}")

    if not os.path.exists(html_path):
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Frontend not found</h1>
            <p>Looking for: {html_path}</p>
            <p>Current working dir: {os.getcwd()}</p>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=404)

    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"DEBUG: Successfully read HTML file ({len(content)} chars)")
            return HTMLResponse(content=content)
    except Exception as e:
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error loading frontend</h1>
            <p>Error: {str(e)}</p>
            <p>Path: {html_path}</p>
        </body>
        </html>
        """
        print(f"DEBUG: Error reading file: {e}")
        return HTMLResponse(content=error_html, status_code=500)
