#!/usr/bin/env python3
"""
启动脚本
"""
import warnings
import os
import sys

# 在导入任何模块之前，先抑制所有 ResourceWarning 警告
# 这些警告来自 aiohttp 的未关闭会话，不影响功能
warnings.simplefilter("ignore", ResourceWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)

# 也可以通过环境变量设置（作为备选方案）
os.environ.setdefault("PYTHONWARNINGS", "ignore::ResourceWarning")

# 创建一个过滤器来过滤 stderr 中的 aiohttp 警告
class AiohttpWarningFilter:
    """过滤 stderr 中的 aiohttp 未关闭会话警告"""
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
        # 保存原始 stderr 的所有属性
        for attr in ['buffer', 'encoding', 'errors', 'line_buffering', 'mode', 'name', 'newlines', 'closed']:
            if hasattr(original_stderr, attr):
                setattr(self, attr, getattr(original_stderr, attr))
    
    def write(self, text):
        # 过滤掉 aiohttp 相关的未关闭警告
        if any(keyword in text for keyword in [
            "Unclosed client session",
            "Unclosed connector",
            "Unclosed connection",
            "client_session:",
            "connector:",
            "connections:"
        ]):
            return len(text)  # 返回长度但不实际写入
        return self.original_stderr.write(text)
    
    def flush(self):
        return self.original_stderr.flush()
    
    def __getattr__(self, name):
        # 代理所有其他属性到原始 stderr
        return getattr(self.original_stderr, name)

# 替换 stderr 以过滤警告
sys.stderr = AiohttpWarningFilter(sys.stderr)

import uvicorn
from config.settings import get_settings
from utils.logger import setup_logger

if __name__ == "__main__":
    # 设置日志
    setup_logger()
    
    # 获取配置
    settings = get_settings()
    
    # 启动服务
    # 确保环境变量设置（对 reload 模式也有效）
    os.environ["PYTHONWARNINGS"] = "ignore::ResourceWarning"
    
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

