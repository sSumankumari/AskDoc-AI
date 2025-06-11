import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'pdf'}

    # Vector store settings
    VECTOR_STORE_PATH = 'vector_stores'
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

    # Text processing settings
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    MAX_TOKENS = 512

    # Groq model settings
    GROQ_MODEL = 'llama3-8b-8192'
    GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

    # Web scraping settings
    REQUEST_TIMEOUT = 30
    MAX_URL_LENGTH = 2048

    # Hosting and debugging (read from env)
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required. Please set it in your .env file")
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.VECTOR_STORE_PATH, exist_ok=True)


# No longer needed to define hardcoded HOST/PORT/DEBUG in sub-classes
class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, config['default'])
