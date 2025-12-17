"""
交易所抽象基类
定义所有交易所必须实现的统一接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal


class BaseExchange(ABC):
    """交易所抽象基类"""
    
    def __init__(self, api_key: str, secret_key: str, **kwargs):
        """
        初始化交易所
        
        Args:
            api_key: API密钥
            secret_key: 密钥
            **kwargs: 其他交易所特定参数
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.name = self.__class__.__name__
    
    @abstractmethod
    def get_balance(self, currency: Optional[str] = None) -> Dict[str, Any]:
        """
        获取账户余额
        
        Args:
            currency: 币种，如果为None则返回所有余额
            
        Returns:
            余额信息字典
        """
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        获取交易对价格信息
        
        Args:
            symbol: 交易对符号，如 'BTC/USDT'
            
        Returns:
            价格信息字典，包含 price, bid, ask 等
        """
        pass
    
    @abstractmethod
    def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        获取订单簿
        
        Args:
            symbol: 交易对符号
            limit: 返回深度数量
            
        Returns:
            订单簿信息，包含 bids 和 asks
        """
        pass
    
    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        下单
        
        Args:
            symbol: 交易对符号
            side: 买卖方向 'buy' 或 'sell'
            order_type: 订单类型 'limit' 或 'market'
            quantity: 数量
            price: 价格（限价单必填）
            **kwargs: 其他订单参数
            
        Returns:
            订单信息字典，包含 order_id, status 等
        """
        pass
    
    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        取消订单
        
        Args:
            symbol: 交易对符号
            order_id: 订单ID
            
        Returns:
            取消结果
        """
        pass
    
    @abstractmethod
    def get_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        查询订单
        
        Args:
            symbol: 交易对符号
            order_id: 订单ID
            
        Returns:
            订单详细信息
        """
        pass
    
    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取未成交订单列表
        
        Args:
            symbol: 交易对符号，如果为None则返回所有未成交订单
            
        Returns:
            订单列表
        """
        pass
    
    @abstractmethod
    def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取K线数据
        
        Args:
            symbol: 交易对符号
            interval: K线周期，如 '1m', '5m', '1h', '1d'
            limit: 返回数量
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            
        Returns:
            K线数据列表
        """
        pass
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        标准化交易对符号（子类可重写）
        
        Args:
            symbol: 原始交易对符号
            
        Returns:
            标准化后的符号
        """
        return symbol.upper()
    
    def __repr__(self):
        return f"<{self.name} Exchange>"

