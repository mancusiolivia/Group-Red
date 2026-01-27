"""
Configuration settings for the application
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the base directory (parent of server directory)
# Since we're in server/core/, we need to go up 2 levels to get to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLIENT_STATIC_DIR = os.path.join(BASE_DIR, "client", "static")
CLIENT_HTML_DIR = os.path.join(BASE_DIR, "client")

# Database Configuration
DATABASE_DIR = os.path.join(BASE_DIR, "data")
DATABASE_PATH = os.path.join(DATABASE_DIR, "app.db")

# Together.ai API Configuration
TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY", "tgp_v1_pMCB-qUW938Aww7f-PUcrwi_u_qzgxmDBlfSCaCbwrw")
TOGETHER_AI_API_URL = "https://api.together.xyz/v1/chat/completions"

# Using a serverless model that's available on Together.ai
# Common serverless models (try these if one doesn't work):
# - mistralai/Mixtral-8x7B-Instruct-v0.1 (most commonly available)
# - meta-llama/Llama-2-70b-chat-hf
# - Qwen/Qwen2.5-72B-Instruct
# - NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO
TOGETHER_AI_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"  # Serverless model - commonly available
