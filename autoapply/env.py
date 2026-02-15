import os

from dotenv import load_dotenv

load_dotenv("dev.env")

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "openai/gpt-oss-120b:free"
RESUME_PATH = "data/resumes/aws/shashank_reddy.pdf"
RESUME_PATH_DOC = "data/resumes/aws/shashank_reddy.docx"

if not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY is not set. "
        "Get a key at https://openrouter.ai/keys"
    )

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS")