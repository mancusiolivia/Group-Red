# Coding Prompts

This document archives all prompts used during the coding/implementation phase.

## FastAPI Backend Implementation

**Prompt**: "Write a FastAPI application that:
1. Serves static files from a client directory
2. Has an endpoint to generate questions using together.ai API
3. Uses prompt templates that are completed with domain information
4. Parses LLM responses (JSON) and handles errors
5. Has endpoints for submitting student responses
6. Grades responses using LLM with rubric-based evaluation
7. Returns structured grading results

Include proper error handling, CORS middleware, and data models using Pydantic."

**AI Response**: [Complete FastAPI implementation with all endpoints]

## Frontend JavaScript Implementation

**Prompt**: "Write JavaScript code for a single-page application that:
1. Handles exam setup form submission
2. Displays questions with background info and rubrics
3. Allows navigation between questions
4. Tracks student responses and time spent
5. Submits responses to backend API
6. Displays grading results with score breakdowns
7. Handles loading states and errors

Use vanilla JavaScript (no frameworks) and make it clean and maintainable."

**AI Response**: [Complete frontend JavaScript implementation]

## Prompt Template Implementation

**Prompt**: "Create Python prompt templates for:
1. Question generation - instructs LLM to create questions, rubrics, and background info in specific JSON format
2. Grading - instructs LLM to grade student responses according to rubric and return scores with explanations

The templates should be flexible and include placeholders for domain, instructions, and student responses. They should instruct the LLM to return only valid JSON."

**AI Response**: [Prompt template strings with formatting placeholders]

## LLM Integration Code

**Prompt**: "Write Python code to:
1. Call together.ai API with proper authentication
2. Handle async HTTP requests using httpx
3. Extract JSON from LLM responses (handling markdown code blocks)
4. Handle errors and timeouts gracefully
5. Support different models

Include proper error handling and response parsing."

**AI Response**: [Async LLM integration function with error handling]
