"""
账户管理器
负责账户余额查询和管理
"""
from typing import Dict, List, Optional, Any
from decimal import Decimal
from exchanges.base import BaseExchange


class AccountManager:
    """账户管理器"""
    
    def __init__(self, exchange: BaseExchange):
        """
        初始化账户管理器
        
        Args:
            exchange: 交易所实例
        """
        self.exchange = exchange
        self._balance_cache: Dict[str, Dict[str, Any]] = {}
    
    def get_balance(self, currency: Optional[str] = None) -> Dict[str, Any]:
        """
        获取账户余额
        
        Args:
            currency: 币种，如果为None则返回所有余额
            
        Returns:
            余额信息
        """
        balance = self.exchange.get_balance(currency)
        
        # 更新缓存
        if currency:
            self._balance_cache[currency] = balance
        else:
            # 如果返回所有余额，更新缓存
            if isinstance(balance, dict) and 'balances' in balance:
                for b in balance['balances']:
                    self._balance_cache[b.get('currency')] = b
        
        return balance
    
    def get_available_balance(self, currency: str) -> Decimal:
        """
        获取可用余额
        
        Args:
            currency: 币种
            
        Returns:
            可用余额
        """
        balance = self.get_balance(currency)
        if isinstance(balance, dict):
            available = balance.get('available', '0')
            return Decimal(str(available))
        return Decimal('0')
    
    def get_total_balance(self, currency: str) -> Decimal:
        """
        获取总余额（可用+冻结）
        
        Args:
            currency: 币种
            
        Returns:
            总余额
        """
        balance = self.get_balance(currency)
        if isinstance(balance, dict):
            total = balance.get('total', balance.get('available', '0'))
            return Decimal(str(total))
        return Decimal('0')
    
    def has_sufficient_balance(
        self,
        currency: str,
        required_amount: Decimal
    ) -> bool:
        """
        检查是否有足够的余额
        
        Args:
            currency: 币种
            required_amount: 所需金额
            
        Returns:
            是否有足够余额
        """
        available = self.get_available_balance(currency)
        return available >= required_amount

