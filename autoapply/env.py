import os

from dotenv import load_dotenv

load_dotenv("dev.env")

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
APPLICATIONS_DIR = "data/applications"

# LLM configuration — defaults to OpenRouter, override for local vLLM
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.getenv("LLM_MODEL", "anthropic/claude-haiku-4.5")
FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "openai/gpt-oss-120b")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Only require the API key when routing through OpenRouter
if "openrouter.ai" in LLM_BASE_URL and not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY is not set. Get a key at https://openrouter.ai/keys"
    )

origins_str = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [
    origin.strip() for origin in origins_str.split(",") if origin.strip()
]
