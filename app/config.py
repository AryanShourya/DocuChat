from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    APP_NAME:str
    APP_VERSION: str 
    DEBUG:bool
    DATABASE_URL:str
    CLERK_JWKS_URL: str = "https://placeholder.clerk.accounts.dev/.well-known/jwks.json"
    GROQ_API_KEY: str 
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10
    CHROMA_DIR: str = "chroma_db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        extra = "ignore"
    )


settings = Settings()
