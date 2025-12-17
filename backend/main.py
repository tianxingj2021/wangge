"""
FastAPI主应用
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

# 替换 stderr 以过滤警告（如果还没有替换）
if not isinstance(sys.stderr, AiohttpWarningFilter):
    sys.stderr = AiohttpWarningFilter(sys.stderr)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.api import api_router
from utils.logger import setup_logger, get_logger
from config.settings import get_settings
from core.config_manager import get_config_manager
from core.exchange_pool import ExchangeInstancePool

# 设置日志
setup_logger()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("=" * 60)
    logger.info("正在启动网格交易系统...")
    logger.info("=" * 60)
    
    # 初始化已配置的交易所
    try:
        config_manager = get_config_manager()
        all_exchanges = config_manager.get_all_exchanges()
        
        if all_exchanges:
            logger.info(f"发现 {len(all_exchanges)} 个已配置的交易所，开始初始化...")
            for exchange_name, exchange_config in all_exchanges.items():
                try:
                    account_key = exchange_config.get('account_key', exchange_name)
                    exchange_display_name = exchange_config.get('name', exchange_name)
                    testnet = exchange_config.get('testnet', False)
                    testnet_str = " (测试网)" if testnet else ""
                    
                    logger.info(f"正在初始化交易所: {exchange_display_name}{testnet_str} (account_key: {account_key})...")
                    
                    # 通过 get_managers 初始化交易所（这会创建实例并保存到池中）
                    managers = ExchangeInstancePool.get_managers(account_key)
                    exchange = ExchangeInstancePool.get_exchange(account_key)
                    
                    if exchange:
                        logger.info(f"✓ 交易所 {exchange_display_name}{testnet_str} 初始化成功")
                    else:
                        logger.warning(f"✗ 交易所 {exchange_display_name}{testnet_str} 初始化失败：无法获取实例")
                        
                except Exception as e:
                    logger.error(f"✗ 交易所 {exchange_name} 初始化失败: {str(e)}", exc_info=True)
            
            logger.info(f"交易所初始化完成，共 {len(all_exchanges)} 个")
        else:
            logger.info("未发现已配置的交易所，将在首次使用时初始化")
        
        logger.info("=" * 60)
        logger.info("应用启动完成")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"启动时初始化交易所失败: {str(e)}", exc_info=True)
    
    yield
    
    # 关闭时清理
    logger.info("正在关闭应用...")
    try:
        ExchangeInstancePool.clear()
        logger.info("已清理所有交易所实例")
    except Exception as e:
        logger.error(f"清理交易所实例失败: {str(e)}", exc_info=True)
    logger.info("应用已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="网格交易系统",
    description="一个模块化的网格交易系统API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router)

# 静态文件和模板
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
static_dir = os.path.join(frontend_dir, "static")
templates_dir = os.path.join(frontend_dir, "templates")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """首页"""
    html_file = os.path.join(templates_dir, "index.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <html>
        <head><title>网格交易系统</title></head>
        <body>
            <h1>网格交易系统 API</h1>
            <p>API文档: <a href="/docs">/docs</a></p>
            <p>API路由: <a href="/api/v1">/api/v1</a></p>
        </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "服务运行正常"}


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )

