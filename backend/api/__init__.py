"""
API路由模块
"""

from fastapi import APIRouter

# 创建主路由器
api_router = APIRouter(prefix="/api/v1")

# 导入子路由
from backend.api import exchange, order, strategy, config, websocket

# 注册路由
api_router.include_router(config.router)
api_router.include_router(exchange.router)
api_router.include_router(order.router)
api_router.include_router(strategy.router)
api_router.include_router(websocket.router)

