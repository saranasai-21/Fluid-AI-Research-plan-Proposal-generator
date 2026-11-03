"""
Fluid AI — Configuration Module
Centralizes all settings, API keys, and constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── Project Paths ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── LLM Configuration ──────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "4096"))

# ─── Retry Configuration ────────────────────────────────────────────────────
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "1.0"))  # seconds
RETRY_MAX_DELAY = float(os.getenv("RETRY_MAX_DELAY", "30.0"))   # seconds

# ─── Agent Configuration ────────────────────────────────────────────────────
REFLECTION_QUALITY_THRESHOLD = float(os.getenv("REFLECTION_QUALITY_THRESHOLD", "7.0"))
MAX_REFINEMENT_PASSES = int(os.getenv("MAX_REFINEMENT_PASSES", "1"))

# ─── Document Configuration ─────────────────────────────────────────────────
DOCUMENT_FONT = "Calibri"
DOCUMENT_TITLE_SIZE = 24
DOCUMENT_HEADING_SIZE = 14
DOCUMENT_BODY_SIZE = 11
