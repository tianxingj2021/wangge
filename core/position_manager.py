"""
持仓管理器
负责持仓信息的查询和管理
"""
from typing import Dict, List, Optional, Any
from decimal import Decimal
from exchanges.base import BaseExchange


class PositionManager:
    """持仓管理器"""
    
    def __init__(self, exchange: BaseExchange):
        """
        初始化持仓管理器
        
        Args:
            exchange: 交易所实例
        """
        self.exchange = exchange
        self._positions: Dict[str, Dict[str, Any]] = {}
    
    def get_position(self, symbol: str) -> Dict[str, Any]:
        """
        获取持仓信息
        
        Args:
            symbol: 交易对符号
            
        Returns:
            持仓信息
        """
        # 如果交易所支持持仓查询，优先从交易所获取
        if hasattr(self.exchange, 'get_position'):
            try:
                position = self.exchange.get_position(symbol)
                if position:
                    # 更新缓存
                    self._positions[symbol] = position
                    return position
            except Exception as e:
                # 如果获取持仓失败，记录错误但不抛出异常，使用缓存或返回空持仓
                error_msg = str(e)
                # 如果是超时错误，不频繁打印日志
                if '超时' not in error_msg and 'timeout' not in error_msg.lower():
                    print(f"从交易所获取持仓失败: {e}")
        
        # 如果有缓存，返回缓存
        if symbol in self._positions:
            return self._positions[symbol]
        
        # 如果没有缓存，返回空持仓
        return {
            'symbol': symbol,
            'quantity': Decimal('0'),
            'avg_price': Decimal('0'),
            'unrealized_pnl': Decimal('0'),
            'side': 'none'
        }
    
    def update_position(self, symbol: str, position_data: Dict[str, Any]):
        """
        更新持仓信息
        
        Args:
            symbol: 交易对符号
            position_data: 持仓数据
        """
        self._positions[symbol] = {
            'symbol': symbol,
            **position_data,
            'updated_at': None  # 可以添加时间戳
        }
    
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """
        获取所有持仓
        
        Returns:
            持仓列表
        """
        return list(self._positions.values())

