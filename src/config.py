import os
from dotenv import load_dotenv

load_dotenv()   # read .env into environment variables

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
