from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    elevenlabs_api_key: str
    elevenlabs_agent_id: str = ""
    elevenlabs_llm: str = "claude-3-5-sonnet"
    elevenlabs_voice_id: str = "EXAVITQu4vr4xnSDxMaL"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    server_url: str = "http://localhost:8000"
    validate_twilio_signature: bool = True

    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("elevenlabs_api_key", "elevenlabs_agent_id", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


settings = Settings()
