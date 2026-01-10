"""
LLM Service Module
Handles all interactions with the Together.ai LLM API.
This module can be reused by both FastAPI endpoints and standalone scripts.
"""

import os
from together import Together

# CSC394 / IS376 YOUR TOGETHER.AI KEY GOES HERE:
# Get API key from environment variable, or use default for development
API_KEY = os.getenv('TOGETHER_API_KEY', 'tgp_v1_pMCB-qUW938Aww7f-PUcrwi_u_qzgxmDBlfSCaCbwrw')
MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

# Initialize the Together client
client = Together(api_key=API_KEY)

# calls the llm api with the given prompt and returns the response
def call_llm(prompt: str, model: str = MODEL) -> str:
    """
    Calls the LLM API with the given prompt and returns the response.
    
    Args:
        prompt: The prompt/question to send to the LLM
        model: The model to use (defaults to MODEL constant)
    
    Returns:
        str: The LLM's response text
    
    Raises:
        Exception: If the API call fails
    """
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        
        result = ''
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                result += chunk.choices[0].delta.content
        
        return result
        
    except Exception as e:
        raise Exception(f"LLM API call failed: {str(e)}")


