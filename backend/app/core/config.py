from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    llm_provider: str = "azure_openai"

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_deployment: str = ""

    

    jwt_secret_key: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    sqlite_db_path: str = "../storage/nbc_platform.db"
    chroma_persist_dir: str = "../storage/chroma"
    documents_dir: str = "../storage/documents"
    generated_dir: str = "../storage/generated"

    # Optional manual driver paths for Application Explorer's Python Selenium browser. If unset,
    # Selenium Manager auto-downloads the matching driver - which itself needs outbound internet
    # access and can fail with a DNS error on a locked-down corporate network, same root cause as
    # the ChromaDB embedding model download. Set these if that happens.
    chrome_driver_path: str = ""
    edge_driver_path: str = ""

    def resolved_path(self, relative: str) -> Path:
        path = (BACKEND_DIR / relative).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def sqlite_url(self) -> str:
        db_path = (BACKEND_DIR / self.sqlite_db_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path.as_posix()}"


settings = Settings()
