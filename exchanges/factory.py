"""
交易所工厂
用于创建和管理交易所实例
"""
from typing import Dict, Type, Optional
from exchanges.base import BaseExchange


class ExchangeFactory:
    """交易所工厂类"""
    
    _exchanges: Dict[str, Type[BaseExchange]] = {}
    
    @classmethod
    def register(cls, name: str, exchange_class: Type[BaseExchange]):
        """
        注册交易所类
        
        Args:
            name: 交易所名称（小写）
            exchange_class: 交易所类
        """
        cls._exchanges[name.lower()] = exchange_class
    
    @classmethod
    def create(
        cls,
        name: str,
        api_key: str,
        secret_key: str,
        **kwargs
    ) -> BaseExchange:
        """
        创建交易所实例
        
        Args:
            name: 交易所名称
            api_key: API密钥
            secret_key: 密钥
            **kwargs: 其他参数
            
        Returns:
            交易所实例
            
        Raises:
            ValueError: 如果交易所未注册
        """
        name_lower = name.lower()
        if name_lower not in cls._exchanges:
            available = ', '.join(cls._exchanges.keys())
            raise ValueError(
                f"交易所 '{name}' 未注册。可用交易所: {available}"
            )
        
        exchange_class = cls._exchanges[name_lower]
        return exchange_class(api_key, secret_key, **kwargs)
    
    @classmethod
    def list_exchanges(cls) -> list:
        """
        获取所有已注册的交易所列表
        
        Returns:
            交易所名称列表
        """
        return list(cls._exchanges.keys())


def get_exchange(
    name: str,
    api_key: str,
    secret_key: str,
    **kwargs
) -> BaseExchange:
    """
    便捷函数：获取交易所实例
    
    Args:
        name: 交易所名称
        api_key: API密钥
        secret_key: 密钥
        **kwargs: 其他参数
        
    Returns:
        交易所实例
    """
    return ExchangeFactory.create(name, api_key, secret_key, **kwargs)

