import os
import logging

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# AI Provider Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# AI Provider Models
# Updated to gemini-3.8-flash as 2.5 is deprecating on Oct 16, 2026
GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"
CEREBRAS_MODEL = "llama3.1-70b"
OPENROUTER_MODEL = "google/gemini-2.5-flash:free" # Or any free model you prefer on OpenRouter

# Provider Order for Fallback (Gemini is used separately for PDF)
PROVIDER_ORDER = ["groq", "cerebras", "openrouter", "gemini"]

# Supported Subjects
SUBJECTS = ["physics", "chemistry", "maths", "biology", "hindi", "english"]

# Database File
DB_FILE = "bot_database.db"
