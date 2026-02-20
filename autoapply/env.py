import os

from dotenv import load_dotenv

load_dotenv("dev.env")

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
FALLBACK_MODEL = "openai/gpt-oss-120b"
# openai/gpt-oss-120b
MODEL = "anthropic/claude-haiku-4.5"
# anthropic/claude-haiku-4.5
APPLICATIONS_DIR = "data/applications"

if not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY is not set. Get a key at https://openrouter.ai/keys"
    )

origins_str = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [
    origin.strip() for origin in origins_str.split(",") if origin.strip()
]

# Authentication configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

if not GOOGLE_CLIENT_ID:
    raise ValueError("GOOGLE_CLIENT_ID environment variable is not set")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is not set")
