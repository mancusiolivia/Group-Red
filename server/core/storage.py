"""
In-memory storage for exams and student responses
In production, this should be replaced with a database
"""
from typing import Dict

# In-memory storage dictionaries
exams_storage: Dict[str, Dict] = {}
student_responses_storage: Dict[str, Dict] = {}
