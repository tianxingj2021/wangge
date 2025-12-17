"""
交易所接口模块
提供统一的交易所接口抽象，支持多交易所扩展
"""

from exchanges.base import BaseExchange
from exchanges.factory import ExchangeFactory, get_exchange

# 导入所有交易所实现以触发注册
try:
    from exchanges import binance  # 触发BinanceExchange注册
except ImportError:
    pass

try:
    from exchanges import extended  # 触发ExtendedExchange注册
except ImportError:
    pass

__all__ = ['BaseExchange', 'ExchangeFactory', 'get_exchange']

