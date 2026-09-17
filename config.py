import os
import logging

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Token (यह Secrets से ही रहने दें ताकि बॉट सुरक्षित रहे)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# ==========================================
# APMIX.AI SETUP (बिना Secret Key के, सीधे यहाँ पेस्ट करें)
# ==========================================
APMIX_API_KEY = "apx_live_qFdzTbts8ES3WEv6LvNxakdB7qwV7wrvvz6Ajkdo"
APMIX_MODEL = "gemini-3-flash-preview-free" # आप इसे 'claude-sonnet-4-6-free' भी कर सकते हैं

# Other AI Provider Keys (Fallback के लिए, Secrets से)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Other Models
GEMINI_MODEL = "gemini-3.6-flash" # PDF पढ़ने के लिए
GROQ_MODEL = "llama-3.3-70b-versatile"
CEREBRAS_MODEL = "llama3.1-70b"
OPENROUTER_MODEL = "google/gemini-2.5-flash:free"

# Provider Order (अब APMix सबसे पहले काम करेगा!)
PROVIDER_ORDER = ["apmix", "groq", "cerebras", "openrouter", "gemini"]

# Supported Subjects
SUBJECTS = ["physics", "chemistry", "maths", "biology", "hindi", "english"]

# Database File
DB_FILE = "bot_database.db"
