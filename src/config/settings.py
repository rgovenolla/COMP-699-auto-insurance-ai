import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # Project Settings
    PROJECT_NAME = "Auto Insurance Liability AI System"
    VERSION = "0.2.0"

    # API Settings
    API_V1_STR = "/api/v1"

    # OpenAI Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Classification Settings
    EMBEDDING_MODEL = "text-embedding-ada-002"
    MAX_TOKENS = 8000
    BATCH_SIZE = 50

    # Cache Settings
    CACHE_EXPIRATION = 3600  # 1 hour

settings = Settings()
