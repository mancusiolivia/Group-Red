# Design Prompts

This document archives all prompts used during the design phase of the Essay Testing and Evaluation System.

## Initial System Design

**Prompt**: "Design a client/server web application for an essay testing system that:
- Generates essay questions in real-time using LLM (together.ai)
- Uses prompt templates that are completed programmatically in Python
- Presents questions to students via web interface
- Accepts essay responses from students
- Grades responses using LLM with detailed rubrics
- Returns structured grading results with explanations

The system should use FastAPI/uvicorn for the server and a modern web interface for the client. Design the architecture, data flow, and key components."

**AI Response**: [Architecture design with client/server separation, prompt template system, LLM integration points, data models]

## UI/UX Design

**Prompt**: "Design a modern, user-friendly web interface for students taking essay exams. The interface should:
- Display background information clearly
- Show questions with proper formatting
- Provide large text areas for essay responses
- Allow navigation between multiple questions
- Display grading results with score breakdowns and feedback
- Be responsive and visually appealing

Create a clean, professional design that's easy to use during exam conditions."

**AI Response**: [UI design with card-based layout, color scheme, navigation elements, results display]

## Data Structure Design

**Prompt**: "Design the data structures for:
1. Question generation response from LLM (background info, question, rubric)
2. Student response submission
3. Grading result from LLM (scores, explanations, feedback)

These should be JSON-compatible Python data structures that can be easily passed to/from the LLM and stored/transmitted over the web."

**AI Response**: [Pydantic models and JSON schema designs]
