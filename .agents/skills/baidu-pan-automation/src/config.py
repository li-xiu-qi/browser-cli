"""项目配置管理."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 百度账号
    baidu_username: str = Field(default="", alias="BAIDU_USERNAME")
    baidu_password: str = Field(default="", alias="BAIDU_PASSWORD")
    use_qr_login: bool = Field(default=True, alias="USE_QR_LOGIN")

    # 本地路径
    local_sync_dir: Path = Field(default=Path.home() / "Documents/BaiduSync", alias="LOCAL_SYNC_DIR")
    transcript_output_dir: Path = Field(
        default=Path.home() / "Documents/Transcripts", alias="TRANSCRIPT_OUTPUT_DIR"
    )
    temp_dir: Path = Field(default=Path("/tmp/baidu-pan-automation"), alias="TEMP_DIR")

    # 浏览器配置
    headless: bool = Field(default=False, alias="HEADLESS")
    browser_width: int = Field(default=1280, alias="BROWSER_WIDTH")
    browser_height: int = Field(default=800, alias="BROWSER_HEIGHT")
    slow_mo: int = Field(default=0, alias="SLOW_MO")

    # 任务配置
    sync_interval: int = Field(default=300, alias="SYNC_INTERVAL")
    transcript_poll_interval: int = Field(default=30, alias="TRANSCRIPT_POLL_INTERVAL")
    max_retry: int = Field(default=3, alias="MAX_RETRY")

    # 日志
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: Path = Field(default=Path("logs/baidu-pan.log"), alias="LOG_FILE")

    def __post_init__(self):
        """确保目录存在."""
        self.local_sync_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()
