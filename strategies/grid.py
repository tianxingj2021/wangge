"""
网格交易策略
在价格区间内设置买卖网格，自动低买高卖
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from strategies.base import BaseStrategy
from core.order_manager import OrderManager
from core.account_manager import AccountManager
from core.position_manager import PositionManager


class GridStrategy(BaseStrategy):
    """网格交易策略"""
    
    def __init__(
        self,
        order_manager: OrderManager,
        account_manager: AccountManager,
        position_manager: PositionManager,
        account_key: Optional[str] = None,
        **kwargs
    ):
        """
        初始化网格策略
        
        Args:
            order_manager: 订单管理器
            account_manager: 账户管理器
            position_manager: 持仓管理器
            account_key: 账号唯一标识
            **kwargs:
                - symbol: 交易对符号（必填）
                - upper_price: 网格上边界价格（必填）
                - lower_price: 网格下边界价格（必填）
                - grid_count: 网格数量（必填）
                - investment: 总投资金额（必填）
                - order_type: 订单类型，默认'limit'
        """
        super().__init__(order_manager, account_manager, position_manager, account_key=account_key, **kwargs)
        
        self.symbol = kwargs.get('symbol')
        self.upper_price = Decimal(str(kwargs.get('upper_price', 0)))
        self.lower_price = Decimal(str(kwargs.get('lower_price', 0)))
        self.grid_count = int(kwargs.get('grid_count', 10))
        self.investment = Decimal(str(kwargs.get('investment', 0)))
        self.order_type = kwargs.get('order_type', 'limit')
        
        self.grid_levels: List[Decimal] = []
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        self.filled_orders: List[Dict[str, Any]] = []
        
        self._calculate_grid_levels()
    
    def _calculate_grid_levels(self):
        """计算网格价格层级"""
        if self.upper_price <= self.lower_price:
            raise ValueError("上边界价格必须大于下边界价格")
        
        price_range = self.upper_price - self.lower_price
        grid_step = price_range / (self.grid_count - 1)
        
        self.grid_levels = []
        for i in range(self.grid_count):
            price = self.lower_price + grid_step * i
            self.grid_levels.append(price.quantize(Decimal('0.01'), rounding=ROUND_DOWN))
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self.symbol:
            raise ValueError("交易对符号不能为空")
        if self.upper_price <= self.lower_price:
            raise ValueError("上边界价格必须大于下边界价格")
        if self.grid_count < 2:
            raise ValueError("网格数量至少为2")
        if self.investment <= 0:
            raise ValueError("投资金额必须大于0")
        return True
    
    def start(self) -> Dict[str, Any]:
        """启动网格策略"""
        if self.is_running:
            return {'status': 'already_running', 'message': '策略已在运行中'}
        
        # 验证配置
        self.validate_config()
        
        # 获取当前价格
        ticker = self.order_manager.exchange.get_ticker(self.symbol)
        current_price = Decimal(str(ticker.get('price', 0)))
        
        if current_price <= 0:
            return {'status': 'error', 'message': '无法获取当前价格'}
        
        # 初始化网格订单
        self._initialize_grid_orders(current_price)
        
        self.is_running = True
        
        return {
            'status': 'started',
            'symbol': self.symbol,
            'grid_count': self.grid_count,
            'current_price': str(current_price),
            'active_orders': len(self.active_orders)
        }
    
    def _initialize_grid_orders(self, current_price: Decimal):
        """初始化网格订单"""
        # 找到当前价格所在的网格位置
        current_grid_index = self._find_grid_index(current_price)
        
        # 在当前价格上方设置卖单
        for i in range(current_grid_index + 1, len(self.grid_levels)):
            price = self.grid_levels[i]
            quantity = self._calculate_order_quantity(price)
            
            if quantity > 0:
                try:
                    order = self.order_manager.place_order(
                        symbol=self.symbol,
                        side='sell',
                        order_type=self.order_type,
                        quantity=quantity,
                        price=price
                    )
                    self.active_orders[order['order_id']] = {
                        **order,
                        'grid_level': i,
                        'grid_price': price
                    }
                except Exception as e:
                    # 记录错误但继续
                    print(f"下单失败: {e}")
        
        # 在当前价格下方设置买单
        for i in range(current_grid_index - 1, -1, -1):
            price = self.grid_levels[i]
            quantity = self._calculate_order_quantity(price)
            
            if quantity > 0:
                try:
                    order = self.order_manager.place_order(
                        symbol=self.symbol,
                        side='buy',
                        order_type=self.order_type,
                        quantity=quantity,
                        price=price
                    )
                    self.active_orders[order['order_id']] = {
                        **order,
                        'grid_level': i,
                        'grid_price': price
                    }
                except Exception as e:
                    print(f"下单失败: {e}")
    
    def _find_grid_index(self, price: Decimal) -> int:
        """找到价格所在的网格索引"""
        for i, grid_price in enumerate(self.grid_levels):
            if price <= grid_price:
                return i
        return len(self.grid_levels) - 1
    
    def _calculate_order_quantity(self, price: Decimal) -> Decimal:
        """计算订单数量"""
        # 简单分配：总投资金额平均分配到每个网格
        per_grid_investment = self.investment / self.grid_count
        quantity = per_grid_investment / price
        return quantity.quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
    
    def stop(self) -> Dict[str, Any]:
        """停止网格策略"""
        if not self.is_running:
            return {'status': 'not_running', 'message': '策略未运行'}
        
        # 取消所有未成交订单
        cancel_results = self.order_manager.cancel_all_orders(self.symbol)
        
        self.is_running = False
        self.active_orders.clear()
        
        return {
            'status': 'stopped',
            'canceled_orders': len(cancel_results)
        }
    
    def update(self) -> Dict[str, Any]:
        """更新策略状态"""
        if not self.is_running:
            return {'status': 'not_running'}
        
        # 检查已成交订单
        open_orders = self.order_manager.get_open_orders(self.symbol)
        open_order_ids = {o['order_id'] for o in open_orders}
        
        # 找出已成交的订单
        filled_orders = []
        for order_id, order_info in list(self.active_orders.items()):
            if order_id not in open_order_ids:
                # 订单已成交或取消
                filled_orders.append(order_info)
                self.filled_orders.append(order_info)
                del self.active_orders[order_id]
        
        # 如果有订单成交，补充新的网格订单
        if filled_orders:
            self._rebalance_grid(filled_orders)
        
        return {
            'status': 'updated',
            'active_orders': len(self.active_orders),
            'filled_orders_count': len(self.filled_orders),
            'new_fills': len(filled_orders)
        }
    
    def _rebalance_grid(self, filled_orders: List[Dict[str, Any]]):
        """重新平衡网格"""
        for order_info in filled_orders:
            side = order_info['side']
            grid_level = order_info['grid_level']
            grid_price = order_info['grid_price']
            
            if side == 'buy':
                # 买单成交，在更高价位设置卖单
                if grid_level + 1 < len(self.grid_levels):
                    sell_price = self.grid_levels[grid_level + 1]
                    quantity = self._calculate_order_quantity(sell_price)
                    
                    if quantity > 0:
                        try:
                            order = self.order_manager.place_order(
                                symbol=self.symbol,
                                side='sell',
                                order_type=self.order_type,
                                quantity=quantity,
                                price=sell_price
                            )
                            self.active_orders[order['order_id']] = {
                                **order,
                                'grid_level': grid_level + 1,
                                'grid_price': sell_price
                            }
                        except Exception as e:
                            print(f"补充卖单失败: {e}")
            
            elif side == 'sell':
                # 卖单成交，在更低价位设置买单
                if grid_level - 1 >= 0:
                    buy_price = self.grid_levels[grid_level - 1]
                    quantity = self._calculate_order_quantity(buy_price)
                    
                    if quantity > 0:
                        try:
                            order = self.order_manager.place_order(
                                symbol=self.symbol,
                                side='buy',
                                order_type=self.order_type,
                                quantity=quantity,
                                price=buy_price
                            )
                            self.active_orders[order['order_id']] = {
                                **order,
                                'grid_level': grid_level - 1,
                                'grid_price': buy_price
                            }
                        except Exception as e:
                            print(f"补充买单失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        ticker = self.order_manager.exchange.get_ticker(self.symbol)
        current_price = Decimal(str(ticker.get('price', 0))) if ticker else Decimal('0')
        
        return {
            'is_running': self.is_running,
            'symbol': self.symbol,
            'upper_price': str(self.upper_price),
            'lower_price': str(self.lower_price),
            'grid_count': self.grid_count,
            'current_price': str(current_price),
            'active_orders': len(self.active_orders),
            'filled_orders': len(self.filled_orders),
            'grid_levels': [str(level) for level in self.grid_levels]
        }

