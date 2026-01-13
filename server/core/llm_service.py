"""
LLM service for interacting with Together.ai API
Handles prompt templates, API calls, and JSON extraction
"""
from fastapi import HTTPException
from typing import Dict, Any
import httpx
import json
import re
from server.core.config import TOGETHER_AI_API_KEY, TOGETHER_AI_API_URL, TOGETHER_AI_MODEL


# Prompt Templates
QUESTION_GENERATION_TEMPLATE = """You are an expert educator creating essay exam questions in the domain of: {domain}

{professor_instructions}

Your task is to create {num_questions} essay question(s) with associated grading rubrics. Use your knowledge of {domain} and any information provided above.

IMPORTANT: You must return a JSON array with {num_questions} question object(s). Each question object must have the following structure:
{{
    "background_info": "A comprehensive information sheet about the topic that may be displayed to students as background context",
    "question_text": "The essay question that students will answer",
    "grading_rubric": {{
        "dimensions": [
            {{
                "name": "Dimension name (e.g., 'Understanding of Core Concepts')",
                "description": "What this dimension evaluates",
                "max_points": 10,
                "criteria": [
                    "Criterion 1 for full points",
                    "Criterion 2 for partial points",
                    "Criterion 3 for minimal points"
                ]
            }}
        ],
        "total_points": 30
    }},
    "domain_info": "Specific domain knowledge students should demonstrate in their answer"
}}

Return a JSON array with exactly {num_questions} question object(s) in this format:
[
  {{"background_info": "...", "question_text": "...", "grading_rubric": {{...}}, "domain_info": "..."}},
  {{"background_info": "...", "question_text": "...", "grading_rubric": {{...}}, "domain_info": "..."}},
  ...
]

Return ONLY valid JSON array, no additional text before or after.
"""

GRADING_TEMPLATE = """You are an expert educator grading a student's essay response.

Question: {question_text}

Grading Rubric:
{grading_rubric}

Background Information Provided to Student:
{background_info}

Domain Knowledge Expected:
{domain_info}

Student's Response:
{student_response}

Time Spent: {time_spent} seconds

Your task is to grade this response according to the rubric. Evaluate the student's answer along each dimension in the rubric.

Return a JSON object with this exact structure:
{{
    "scores": {{
        "Dimension Name 1": <score out of max_points>,
        "Dimension Name 2": <score out of max_points>
    }},
    "total_score": <sum of all dimension scores>,
    "explanation": "Detailed explanation of why the student received these scores, referencing specific parts of their answer and the rubric criteria",
    "feedback": "Constructive feedback for the student on how to improve their answer"
}}

Return ONLY valid JSON, no additional text before or after.
"""


async def call_together_ai(prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
    """Call Together.ai API to get LLM response"""
    headers = {
        "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": TOGETHER_AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        print(f"DEBUG: Calling Together.ai API with model: {TOGETHER_AI_MODEL}")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(TOGETHER_AI_API_URL, headers=headers, json=payload)
            print(f"DEBUG: API Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text
                print(f"DEBUG: API Error response: {error_text}")
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Together.ai API error: {error_text}"
                )
            
            result = response.json()
            if "choices" not in result or len(result["choices"]) == 0:
                print(f"DEBUG: Unexpected API response format: {result}")
                raise HTTPException(
                    status_code=500,
                    detail="Unexpected response format from Together.ai API"
                )
            
            content = result["choices"][0]["message"]["content"]
            print(f"DEBUG: Received response from LLM ({len(content)} chars)")
            return content
    except httpx.TimeoutException:
        print("DEBUG: Request to Together.ai timed out")
        raise HTTPException(status_code=500, detail="Request to LLM timed out. Please try again.")
    except httpx.HTTPStatusError as e:
        print(f"DEBUG: HTTP error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=500,
            detail=f"Together.ai API HTTP error: {e.response.status_code} - {e.response.text}"
        )
    except Exception as e:
        print(f"DEBUG: Unexpected error calling Together.ai: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM API error: {str(e)}")


def extract_json_from_response(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM response, handling potential markdown code blocks and extra text"""
    text = text.strip()
    print(f"DEBUG: Extracting JSON from response (first 200 chars: {text[:200]})")
    
    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Find the closing ```
        closing_idx = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip().startswith("```"):
                closing_idx = i
                break
        if closing_idx > 0:
            text = "\n".join(lines[1:closing_idx])
        else:
            text = "\n".join(lines[1:])
        print("DEBUG: Removed markdown code block markers")
    
    # Find the first complete JSON object by matching braces
    start_idx = text.find("{")
    if start_idx == -1:
        raise ValueError("No JSON object found in response")
    
    # Count braces to find the matching closing brace
    brace_count = 0
    end_idx = start_idx
    in_string = False
    escape_next = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
    
    if brace_count != 0:
        # If we couldn't find matching braces, try the old method
        end_idx = text.rfind("}") + 1
        if end_idx <= start_idx:
            raise ValueError("Could not find complete JSON object")
    
    json_str = text[start_idx:end_idx]
    print(f"DEBUG: Extracted JSON string ({len(json_str)} chars)")
    
    try:
        # Try to parse just the JSON part, ignoring any extra text after it
        parsed = json.loads(json_str)
        print("DEBUG: Successfully parsed JSON")
        return parsed
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON parse error: {e}")
        print(f"DEBUG: Problematic JSON string (first 500 chars): {json_str[:500]}")
        # Try to fix common issues
        # Remove any trailing commas before closing braces/brackets
        json_str_fixed = re.sub(r',\s*}', '}', json_str)
        json_str_fixed = re.sub(r',\s*]', ']', json_str_fixed)
        try:
            return json.loads(json_str_fixed)
        except:
            raise ValueError(f"Invalid JSON in LLM response: {str(e)}")
