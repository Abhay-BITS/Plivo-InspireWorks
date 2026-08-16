"""Application settings, validated once at boot rather than scattered through the code."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    plivo_auth_id: str = ""
    plivo_auth_token: str = ""

    plivo_from_number: str = "+918035454161"
    default_destination: str = "+917007745038"
    associate_number: str = "02264236412"

    public_base_url: str = "http://localhost:8000"

    otp_code: str = "0407"

    verify_plivo_signature: bool = True

    demo_mode: bool = True

    action_audio_url: str = "https://s3.amazonaws.com/plivocloud/Trumpet.mp3"

    session_ttl_minutes: int = 30

    @field_validator("otp_code")
    @classmethod
    def otp_code_is_four_digits(cls, value: str) -> str:
        if not (len(value) == 4 and value.isdigit()):
            raise ValueError("OTP_CODE must be exactly four digits")
        return value

    @field_validator("public_base_url")
    @classmethod
    def base_url_has_no_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
