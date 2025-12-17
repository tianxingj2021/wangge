"""
日志配置
"""
import sys
import warnings
from loguru import logger
from config.settings import get_settings


def setup_logger():
    """设置日志配置"""
    settings = get_settings()
    
    # 抑制所有 ResourceWarning（包括 aiohttp 的未关闭会话警告）
    # 这些警告来自 Extended SDK 内部，不影响功能
    warnings.filterwarnings("ignore", category=ResourceWarning)
    
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )
    
    # 添加文件输出
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level=settings.log_level,
        encoding="utf-8"
    )


def get_logger(name: str = None):
    """获取日志器"""
    if name:
        return logger.bind(name=name)
    return logger

