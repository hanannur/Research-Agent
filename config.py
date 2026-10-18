"""
Configuration module for DeepResearch AI.
Loads environment variables and validates system prerequisites.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Silence the banner in pydantic-ai for cleaner logs/UI
os.environ["PYDANTIC_AI_NO_BANNER"] = "1"

# Load environment variables from .env file
load_dotenv(override=False)

BASE_DIR = Path(__file__).resolve().parent

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "research_agent.db")).strip()

# Depth presets for search and analysis
DEPTH_CONFIG = {
    "Quick": {
        "max_queries": 2,
        "max_results_per_query": 3,
        "description": "Fast reconnaissance (~30s, 3-6 total sources)"
    },
    "Standard": {
        "max_queries": 3,
        "max_results_per_query": 4,
        "description": "Balanced deep research (~60s, 8-12 total sources)"
    },
    "Detailed": {
        "max_queries": 5,
        "max_results_per_query": 5,
        "description": "Comprehensive exhaustive investigation (~90-120s, 15-25 total sources)"
    }
}


def validate_api_key() -> tuple[bool, str]:
    """
    Validates that a Gemini API key is configured.
    Returns:
        (is_valid, message)
    """
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "your_gemini_api_key_here":
        return (
            False,
            "GEMINI_API_KEY is not set. Please add your Gemini API key in the .env file or sidebar settings."
        )
    return (True, "Gemini API key is configured.")
