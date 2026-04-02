from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://postgres:dev_password@localhost:5432/eco_dashboard"
    redis_url: str = "redis://localhost:6379/0"
    electricity_maps_api_key: str = ""
    """API key sent as ``auth-token`` header."""

    electricity_maps_tier: Literal["free", "paid"] = "free"
    """Use Electricity Maps free-tier host or commercial ``/v3`` host."""

    electricity_maps_base_url: str | None = None
    """If set, overrides tier-based default base URL (no trailing slash)."""

    watttime_username: str = ""
    watttime_password: str = ""
    watttime_base_url: str = "https://api.watttime.org"

    @property
    def is_watttime_configured(self) -> bool:
        """True when real WattTime credentials are set (not empty / placeholder)."""
        u = (self.watttime_username or "").strip()
        p = (self.watttime_password or "").strip()
        if not u or not p:
            return False
        if u.lower() == "placeholder" or p.lower() == "placeholder":
            return False
        return True

    cors_origins: str = "http://localhost:3000"
    """Comma-separated browser origins for FastAPI CORS."""

    @property
    def cors_origin_list(self) -> list[str]:
        return [s.strip() for s in self.cors_origins.split(",") if s.strip()]

    @property
    def electricity_maps_api_root(self) -> str:
        """Root URL for Electricity Maps paths (e.g. ``carbon-intensity/latest``)."""
        if self.electricity_maps_base_url:
            return self.electricity_maps_base_url.rstrip("/")
        if self.electricity_maps_tier == "paid":
            return "https://api.electricitymaps.com/v3"
        return "https://api-access.electricitymaps.com/free-tier"


settings = Settings()
