"""
配置管理
使用pydantic-settings管理配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 交易所配置
    exchange_name: str = "binance"
    exchange_api_key: str = ""
    exchange_secret_key: str = ""
    exchange_testnet: bool = True
    
    # Extended交易所特定配置
    exchange_private_key: Optional[str] = None  # Extended需要private_key（如果与secret_key不同）
    exchange_public_key: Optional[str] = None  # Extended需要public_key
    exchange_vault: Optional[int] = None  # Extended需要vault ID
    exchange_default_market: str = "BTC-USD"  # Extended默认交易对
    
    # 服务器配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # 其他配置
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

