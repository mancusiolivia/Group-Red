from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from llm_service import call_llm
from datetime import datetime
from typing import List, Dict

''' 
REQUIRES FASTAPI SERVER.
                write endpoints (GET, POST, DELETE, PUT, etc.) in this file.
                calls llm_service.py for llm api calls

command: uvicorn api_server:app - server terminal
command: ./test_server.sh - test terminal
'''
app = FastAPI()

# Storage for POST /projectdemo results
project_demo_results: List[Dict] = []

# Request model for projectdemo endpoint
class ProjectDemoRequest(BaseModel):
    prompt: str | None = None

# GET APIS below-------------------------------------------------------

# GET endpoint to verify server is running when following local host link
@app.get("/")
async def root():
    """Root endpoint to verify server is running."""
    return {"message": "FastAPI server is running. Use POST /projectdemo to call the LLM, or GET /projectdemo to view results."}

# GET endpoint to view all POST /projectdemo results
@app.get("/projectdemo")
async def get_project_demo_results():
    """
    GET endpoint that returns all results from POST /projectdemo requests.
    
    Returns a list of all previous POST requests with their prompts and responses.
    """
    if not project_demo_results:
        return {
            "message": "No results yet. Make a POST request to /projectdemo first.",
            "results": []
        }
    
    return {
        "total_results": len(project_demo_results),
        "results": project_demo_results
    }


# POST APIS below-------------------------------------------------------

# POST endpoint to call the LLM with optional prompt
@app.post("/projectdemo")
async def projectDemo(request: ProjectDemoRequest = None):
    """
    POST endpoint that calls the LLM and returns the response as JSON.
    
    If no prompt is provided, uses default: "user did not enter a prompt"
    If prompt is provided, uses the user's prompt.
    
    Request body (optional):
    {
        "prompt": "Your question or message here"
    }
    
    Or send empty body {} to use default prompt.
    """
    default_prompt = "user did not enter a prompt"
    
    # Determine which prompt to use
    if request is None or request.prompt is None or request.prompt.strip() == "":
        prompt_to_use = default_prompt
        print("Working... (using default prompt)")
    else:
        prompt_to_use = request.prompt
        print(f"Working... (user prompt: {prompt_to_use[:50]}...)")
    
    try:
        result = call_llm(prompt_to_use)
        print(f"Result received: {len(result)} characters")
        
        # Store the result
        result_entry = {
            "timestamp": datetime.now().isoformat(),
            "prompt_used": prompt_to_use,
            "response": result,
            "response_length": len(result)
        }
        project_demo_results.append(result_entry)
        
        return {"response": result}
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
