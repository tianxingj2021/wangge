"""
订单管理器
负责订单的创建、查询、取消等操作
"""
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from exchanges.base import BaseExchange


class OrderManager:
    """订单管理器"""
    
    def __init__(self, exchange: BaseExchange):
        """
        初始化订单管理器
        
        Args:
            exchange: 交易所实例
        """
        self.exchange = exchange
        self._local_orders: Dict[str, Dict[str, Any]] = {}  # 本地订单缓存
    
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        post_only: bool = False,
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
            订单信息
        """
        # 对于限价单，默认设置post_only=True，确保订单挂单而不是立即成交
        if order_type == 'limit' and 'postOnly' not in kwargs and 'post_only' not in kwargs:
            kwargs['postOnly'] = True
        
        # 调用交易所API下单
        order_result = self.exchange.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            **kwargs
        )
        
        # 保存到本地缓存
        order_id = order_result.get('order_id')
        if order_id:
            self._local_orders[order_id] = {
                **order_result,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        
        return order_result
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        取消订单
        
        Args:
            symbol: 交易对符号
            order_id: 订单ID
            
        Returns:
            取消结果
        """
        result = self.exchange.cancel_order(symbol, order_id)
        
        # 更新本地缓存
        if order_id in self._local_orders:
            self._local_orders[order_id]['status'] = 'CANCELED'
            self._local_orders[order_id]['updated_at'] = datetime.now().isoformat()
        
        return result
    
    def get_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        查询订单
        
        Args:
            symbol: 交易对符号
            order_id: 订单ID
            
        Returns:
            订单详细信息
        """
        # 先从交易所查询最新状态
        order = self.exchange.get_order(symbol, order_id)
        
        # 更新本地缓存
        if order_id in self._local_orders:
            self._local_orders[order_id].update(order)
            self._local_orders[order_id]['updated_at'] = datetime.now().isoformat()
        else:
            self._local_orders[order_id] = {
                **order,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        
        return order
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取未成交订单列表
        
        Args:
            symbol: 交易对符号，如果为None则返回所有未成交订单
            
        Returns:
            订单列表
        """
        return self.exchange.get_open_orders(symbol)
    
    def get_local_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取本地缓存的订单列表
        
        Args:
            symbol: 交易对符号，如果为None则返回所有订单
            
        Returns:
            订单列表
        """
        orders = list(self._local_orders.values())
        if symbol:
            orders = [o for o in orders if o.get('symbol') == symbol]
        return orders
    
    def cancel_all_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        取消所有未成交订单
        
        Args:
            symbol: 交易对符号，如果为None则取消所有未成交订单
            
        Returns:
            取消结果列表
        """
        open_orders = self.get_open_orders(symbol)
        results = []
        
        for order in open_orders:
            try:
                result = self.cancel_order(order['symbol'], order['order_id'])
                results.append(result)
            except Exception as e:
                results.append({
                    'order_id': order.get('order_id'),
                    'error': str(e)
                })
        
        return results

