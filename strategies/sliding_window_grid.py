"""
滑动窗口网格交易策略
参考前端策略实现，以当前价格为中心，动态调整买卖单比例
"""
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from datetime import datetime
import time
import threading
from strategies.base import BaseStrategy
from core.order_manager import OrderManager
from core.account_manager import AccountManager
from core.position_manager import PositionManager


class SlidingWindowGridStrategy(BaseStrategy):
    """滑动窗口网格交易策略"""
    
    # ========== 网格策略核心配置 ==========
    GRID_CONFIG = {
        'TOTAL_ORDERS': 18,              # 固定18单滑动窗口
        'WINDOW_PERCENT': Decimal('0.12'),  # 12%窗口宽度
        'SELL_RATIO': Decimal('0.5'),    # 50%卖单
        'BUY_RATIO': Decimal('0.5'),     # 50%买单
        'BASE_PRICE_INTERVAL': Decimal('10'),  # 基础间距
        'SAFE_GAP': Decimal('20'),       # 比当前盘口再偏移一点，防止瞬成
        'MAX_DRIFT_BUFFER': Decimal('2000'),  # 超出窗口太多自动停止扩展
        'MIN_VALID_PRICE': Decimal('10000'),  # 防止崩盘挂到地板价
        'MAX_MULTIPLIER': Decimal('15'),  # 动态开仓大小的比例最大开仓倍数
        'ORDER_COOLDOWN': 1.5,           # 单个订单成功后冷却时间（秒）
    }
    
    def __init__(
        self,
        order_manager: OrderManager,
        account_manager: AccountManager,
        position_manager: PositionManager,
        account_key: Optional[str] = None,
        **kwargs
    ):
        """
        初始化滑动窗口网格策略
        
        Args:
            order_manager: 订单管理器
            account_manager: 账户管理器
            position_manager: 持仓管理器
            **kwargs:
                - symbol: 交易对符号（必填）
                - order_size: 每单数量（必填）
                - total_orders: 总订单数，默认18
                - window_percent: 窗口宽度百分比，默认0.12（12%）
                - sell_ratio: 卖单比例，默认0.5（50%）
                - buy_ratio: 买单比例，默认0.5（50%）
                - base_price_interval: 基础价格间距，默认10
                - safe_gap: 安全偏移，默认20
                - max_drift_buffer: 最大偏移缓冲，默认2000
                - min_valid_price: 最低有效价格，默认10000
                - max_multiplier: 最大开仓倍数，默认15
                - order_cooldown: 订单冷却时间（秒），默认1.5
        """
        super().__init__(order_manager, account_manager, position_manager, account_key=account_key, **kwargs)
        
        self.symbol = kwargs.get('symbol')
        self.order_size = Decimal(str(kwargs.get('order_size', 0)))
        
        if not self.symbol:
            raise ValueError("交易对符号不能为空")
        if self.order_size <= 0:
            raise ValueError("每单数量必须大于0")
        
        # 从kwargs获取配置参数，如果没有则使用默认值
        self.grid_config = {
            'TOTAL_ORDERS': kwargs.get('total_orders', self.GRID_CONFIG['TOTAL_ORDERS']),
            'WINDOW_PERCENT': Decimal(str(kwargs.get('window_percent', self.GRID_CONFIG['WINDOW_PERCENT']))),
            'SELL_RATIO': Decimal(str(kwargs.get('sell_ratio', self.GRID_CONFIG['SELL_RATIO']))),
            'BUY_RATIO': Decimal(str(kwargs.get('buy_ratio', self.GRID_CONFIG['BUY_RATIO']))),
            'BASE_PRICE_INTERVAL': Decimal(str(kwargs.get('base_price_interval', self.GRID_CONFIG['BASE_PRICE_INTERVAL']))),
            'SAFE_GAP': Decimal(str(kwargs.get('safe_gap', self.GRID_CONFIG['SAFE_GAP']))),
            'MAX_DRIFT_BUFFER': Decimal(str(kwargs.get('max_drift_buffer', self.GRID_CONFIG['MAX_DRIFT_BUFFER']))),
            'MIN_VALID_PRICE': Decimal(str(kwargs.get('min_valid_price', self.GRID_CONFIG['MIN_VALID_PRICE']))),
            'MAX_MULTIPLIER': Decimal(str(kwargs.get('max_multiplier', self.GRID_CONFIG['MAX_MULTIPLIER']))),
            'ORDER_COOLDOWN': kwargs.get('order_cooldown', self.GRID_CONFIG['ORDER_COOLDOWN']),
        }
        
        self.order_cooldown = self.grid_config['ORDER_COOLDOWN']
        
        # 策略状态
        self.active_orders: Dict[str, Dict[str, Any]] = {}  # order_id -> order_info
        self.last_order_time: float = 0
        self.cycle_count: int = 0
        
        # 后台更新线程
        self._update_thread: Optional[threading.Thread] = None
        self._update_interval: float = 3.0  # 默认3秒更新一次（参考JavaScript策略的MONITOR_INTERVAL）
        self._stop_update_thread: bool = False
        
        # 合并配置到self.config
        self.config.update(self.grid_config)
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self.symbol:
            raise ValueError("交易对符号不能为空")
        if self.order_size <= 0:
            raise ValueError("每单数量必须大于0")
        return True
    
    def start(self) -> Dict[str, Any]:
        """启动策略"""
        if self.is_running:
            return {'status': 'already_running', 'message': '策略已在运行中'}
        
        self.validate_config()
        
        # 获取当前价格
        ticker = self.order_manager.exchange.get_ticker(self.symbol)
        if not ticker or not ticker.get('price'):
            return {'status': 'error', 'message': '无法获取当前价格'}
        
        self.is_running = True
        self.cycle_count = 0
        self._stop_update_thread = False
        
        # 启动后立即执行第一个交易周期，创建初始订单
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 策略启动，开始创建初始订单...")
        initial_update_result = self.update()
        
        if initial_update_result.get('status') == 'error':
            # 如果初始更新失败，停止策略
            self.is_running = False
            return {
                'status': 'error',
                'message': f'策略启动失败: {initial_update_result.get("message", "未知错误")}',
                'symbol': self.symbol
            }
        
        # 启动后台更新线程
        self._start_update_thread()
        
        return {
            'status': 'started',
            'symbol': self.symbol,
            'order_size': str(self.order_size),
            'total_orders': self.grid_config['TOTAL_ORDERS'],
            'initial_orders': initial_update_result.get('new_orders', 0),
            'active_orders': initial_update_result.get('active_orders', 0)
        }
    
    def stop(self) -> Dict[str, Any]:
        """停止策略"""
        if not self.is_running:
            return {'status': 'not_running', 'message': '策略未运行'}
        
        # 停止后台更新线程
        self._stop_update_thread = True
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=5.0)
        
        # 取消所有未成交订单
        try:
            # 1) 先撤销所有挂单
            open_orders = self.order_manager.get_open_orders(self.symbol)
            canceled_count = 0
            for order in open_orders:
                try:
                    self.order_manager.cancel_order(
                        symbol=self.symbol,
                        order_id=order['order_id']
                    )
                    canceled_count += 1
                except Exception as e:
                    print(f"取消订单失败: {e}")
            
            # 2) 平掉所有持仓（市价平仓，reduceOnly）
            position = self.position_manager.get_position(self.symbol)
            position_qty = Decimal(str(position.get('quantity', 0)))
            close_result = None
            if position_qty != 0:
                close_side = 'sell' if position_qty > 0 else 'buy'  # 多单用卖平，空单用买平
                try:
                    close_result = self.order_manager.place_order(
                        symbol=self.symbol,
                        side=close_side,
                        order_type='market',
                        quantity=abs(position_qty),
                        reduceOnly=True,
                        closePosition=True
                    )
                    print(f"平仓完成: {close_side} {abs(position_qty)} @ 市价")
                except Exception as e:
                    print(f"平仓失败: {e}")
            
            self.is_running = False
            self.active_orders.clear()
            
            return {
                'status': 'stopped',
                'canceled_orders': canceled_count,
                'closed_position': str(position_qty),
                'close_result': close_result
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'停止策略失败: {str(e)}'
            }
    
    def _start_update_thread(self):
        """启动后台更新线程"""
        if self._update_thread and self._update_thread.is_alive():
            return
        
        def update_loop():
            """后台更新循环"""
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 后台更新线程已启动，更新间隔: {self._update_interval}秒")
            while self.is_running and not self._stop_update_thread:
                try:
                    # 执行更新
                    result = self.update()
                    if result.get('status') == 'error':
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 策略更新失败: {result.get('message', '未知错误')}")
                    
                    # 等待更新间隔
                    time.sleep(self._update_interval)
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 后台更新线程异常: {e}")
                    import traceback
                    traceback.print_exc()
                    # 即使出错也继续循环，避免线程退出
                    time.sleep(self._update_interval)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 后台更新线程已退出 (is_running={self.is_running}, _stop_update_thread={self._stop_update_thread})")
        
        self._update_thread = threading.Thread(target=update_loop, daemon=True)
        self._update_thread.start()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 后台更新线程已启动，更新间隔: {self._update_interval}秒")
    
    def update(self) -> Dict[str, Any]:
        """
        更新策略状态（核心方法）
        参考JavaScript策略的executeTradingCycle逻辑
        """
        if not self.is_running:
            return {'status': 'not_running'}
        
        self.cycle_count += 1
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 第{self.cycle_count}次循环")
        
        try:
            # 1. 获取市场数据
            try:
                market_data = self._get_market_data()
                if not market_data['ask_price'] or not market_data['bid_price']:
                    print('无法读取价格，跳过')
                    return {'status': 'error', 'message': '无法获取价格数据'}
            except Exception as e:
                print(f'获取市场数据失败: {e}')
                return {'status': 'error', 'message': f'获取市场数据失败: {e}'}
            
            # 2. 计算目标价格
            try:
                target_result = self._calculate_target_prices(market_data)
            except Exception as e:
                print(f'计算目标价格失败: {e}')
                import traceback
                traceback.print_exc()
                return {'status': 'error', 'message': f'计算目标价格失败: {e}'}
            # 计算订单结果的日志已在_calculate_target_prices中输出，这里不再重复
            
            # 3. 撤销远单
            if target_result['cancel_orders']:
                print(f"开始撤销 {len(target_result['cancel_orders'])} 个远单...")
                canceled_count = 0
                failed_count = 0
                
                for cancel_order in target_result['cancel_orders']:
                    try:
                        # 如果订单有 order_id，直接使用 order_id 取消（用于清理重复订单）
                        if 'order_id' in cancel_order:
                            try:
                                self.order_manager.cancel_order(
                                    symbol=self.symbol,
                                    order_id=cancel_order['order_id']
                                )
                                canceled_count += 1
                                order_type_cn = '买' if cancel_order['type'] == 'buy' else '卖'
                                print(f"已取消重复订单: {order_type_cn}单 @ {cancel_order['price']} (订单ID: {cancel_order['order_id']})")
                                time.sleep(0.5)  # 避免频繁取消订单
                                continue
                            except Exception as e:
                                print(f"取消订单失败 (订单ID: {cancel_order['order_id']}): {e}")
                                failed_count += 1
                                continue
                        
                        # 如果没有 order_id，使用价格和类型查找订单（用于撤销远单）
                        # 检查是否需要跳过撤单（如果价格接近当前价格）
                        current_price = (market_data['ask_price'] + market_data['bid_price']) / 2
                        price_diff = abs(float(cancel_order['price']) - float(current_price))
                        max_diff = float(self.grid_config['BASE_PRICE_INTERVAL']) * (float(self.grid_config['MAX_MULTIPLIER']) / 4)
                        
                        if price_diff <= max_diff:
                            print(f"跳过撤单：价格接近当前价格 (差值: {price_diff:.1f})")
                            continue
                        
                        # 查找并取消订单（设置超时保护，避免卡住整个循环）
                        try:
                            result = self._cancel_order_by_price(cancel_order['price'], cancel_order['type'])
                            if result:
                                canceled_count += 1
                                time.sleep(0.5)  # 避免频繁取消订单
                            else:
                                failed_count += 1
                                # 如果取消失败，继续处理下一个订单，不中断整个循环
                        except Exception as cancel_error:
                            print(f"撤销订单异常: {cancel_error}")
                            failed_count += 1
                            # 继续处理下一个订单，不中断整个循环
                            continue
                    except Exception as e:
                        print(f"撤销订单失败: {e}")
                        failed_count += 1
                        # 继续执行，不中断整个更新循环
                        continue
                
                if canceled_count > 0 or failed_count > 0:
                    print(f"撤销订单完成: 成功 {canceled_count} 个，失败 {failed_count} 个")
            
            # 4. 重新获取市场数据（撤单后）
            updated_market_data = self._get_market_data()
            
            # 5. 重新计算要下的订单
            updated_result = self._calculate_target_prices(updated_market_data)
            
            # 6. 执行下单
            if updated_result['buy_prices'] or updated_result['sell_prices']:
                self._execute_batch_orders(
                    updated_result['buy_prices'],
                    updated_result['sell_prices']
                )
            
            return {
                'status': 'updated',
                'cycle_count': self.cycle_count,
                'active_orders': len(self.active_orders),
                'new_orders': len(updated_result['buy_prices']) + len(updated_result['sell_prices']),
                'canceled_orders': len(target_result['cancel_orders'])
            }
            
        except Exception as e:
            print(f'周期执行异常: {e}')
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _get_market_data(self) -> Dict[str, Any]:
        """获取市场数据（价格和现有订单）"""
        try:
            # 获取ticker
            try:
                ticker = self.order_manager.exchange.get_ticker(self.symbol)
                ask_price = Decimal(str(ticker.get('ask', ticker.get('price', 0))))
                bid_price = Decimal(str(ticker.get('bid', ticker.get('price', 0))))
            except Exception as e:
                print(f"获取ticker失败: {e}")
                raise
            
            # 获取现有订单（不打印价格，与JS策略一致）
            try:
                open_orders = self.order_manager.get_open_orders(self.symbol)
            except Exception as e:
                # 如果获取订单失败，使用空列表，不阻塞策略
                print(f"获取订单列表失败: {e}，使用空订单列表")
                open_orders = []
            
            existing_sell_orders = []
            existing_buy_orders = []
            # 同时统计所有订单（不去重），用于准确统计订单数量
            all_sell_orders_count = 0
            all_buy_orders_count = 0
            # 记录每个价格对应的订单列表（用于清理重复订单）
            sell_orders_by_price = {}  # price -> [order1, order2, ...]
            buy_orders_by_price = {}   # price -> [order1, order2, ...]
            
            for order in open_orders:
                if order.get('side', '').lower() == 'sell':
                    price = order.get('price')
                    if price:
                        price_decimal = Decimal(str(price))
                        existing_sell_orders.append(price_decimal)
                        all_sell_orders_count += 1
                        # 按价格分组订单
                        if price_decimal not in sell_orders_by_price:
                            sell_orders_by_price[price_decimal] = []
                        sell_orders_by_price[price_decimal].append(order)
                elif order.get('side', '').lower() == 'buy':
                    price = order.get('price')
                    if price:
                        price_decimal = Decimal(str(price))
                        existing_buy_orders.append(price_decimal)
                        all_buy_orders_count += 1
                        # 按价格分组订单
                        if price_decimal not in buy_orders_by_price:
                            buy_orders_by_price[price_decimal] = []
                        buy_orders_by_price[price_decimal].append(order)
            
            # 排序并去重（用于判断是否需要下单，每个价格只需要一个订单）
            existing_sell_orders = sorted(set(existing_sell_orders))
            existing_buy_orders = sorted(set(existing_buy_orders), reverse=True)
            
            # 不打印现有订单数量，与JS策略一致
            
            return {
                'ask_price': ask_price,
                'bid_price': bid_price,
                'existing_sell_orders': existing_sell_orders,
                'existing_buy_orders': existing_buy_orders,
                'all_sell_orders_count': all_sell_orders_count,  # 所有卖单数量（不去重）
                'all_buy_orders_count': all_buy_orders_count,    # 所有买单数量（不去重）
                'sell_orders_by_price': sell_orders_by_price,    # 按价格分组的卖单（用于清理重复订单）
                'buy_orders_by_price': buy_orders_by_price        # 按价格分组的买单（用于清理重复订单）
            }
        except Exception as e:
            print(f"获取市场数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'ask_price': None,
                'bid_price': None,
                'existing_sell_orders': [],
                'existing_buy_orders': [],
                'all_sell_orders_count': 0,
                'all_buy_orders_count': 0,
                'sell_orders_by_price': {},
                'buy_orders_by_price': {}
            }
    
    def _calculate_target_prices(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算目标价格
        参考JavaScript策略的calculateTargetPrices逻辑
        """
        ask_price = market_data['ask_price']
        bid_price = market_data['bid_price']
        existing_sell_orders = market_data.get('existing_sell_orders', [])
        existing_buy_orders = market_data.get('existing_buy_orders', [])
        # 获取实际订单数量（不去重），用于准确统计
        all_sell_orders_count = market_data.get('all_sell_orders_count', len(existing_sell_orders))
        all_buy_orders_count = market_data.get('all_buy_orders_count', len(existing_buy_orders))
        # 获取按价格分组的订单（用于清理重复订单）
        sell_orders_by_price = market_data.get('sell_orders_by_price', {})
        buy_orders_by_price = market_data.get('buy_orders_by_price', {})
        # 获取按价格分组的订单（用于清理重复订单）
        sell_orders_by_price = market_data.get('sell_orders_by_price', {})
        buy_orders_by_price = market_data.get('buy_orders_by_price', {})
        
        cfg = self.grid_config
        
        # 计算中间价和窗口
        mid_price = (ask_price + bid_price) / 2
        window_size = mid_price * cfg['WINDOW_PERCENT']
        half_window = window_size / 2
        interval = cfg['BASE_PRICE_INTERVAL']
        
        # 获取持仓信息
        position_info = self._get_position_info()
        position_btc = position_info['position_btc']
        order_size = position_info['order_size']
        
        # 计算理论最大持仓：总订单数 × 每单数量
        total_orders = cfg['TOTAL_ORDERS']
        max_position_theoretical = Decimal(str(total_orders)) * order_size
        
        # 使用MAX_MULTIPLIER作为额外的安全限制，但不应超过理论最大值
        max_multiplier = cfg['MAX_MULTIPLIER']
        safe_order_size = max(order_size, Decimal('0.000001'))
        max_position_by_multiplier = max_multiplier * safe_order_size
        
        # 实际最大持仓限制：取理论最大值和倍数限制中的较小值
        max_position_limit = min(max_position_theoretical, max_position_by_multiplier)
        
        # 计算当前持仓相对于开仓大小的倍数（与JS策略一致）
        position_multiplier = abs(position_btc) / safe_order_size
        
        # 计算当前持仓相对于最大限制的比例
        position_ratio = abs(position_btc) / max(max_position_limit, safe_order_size)
        
        # 基础比例
        base_sell_ratio = cfg['SELL_RATIO']
        base_buy_ratio = cfg['BUY_RATIO']
        
        final_sell_ratio = base_sell_ratio
        final_buy_ratio = base_buy_ratio
        is_at_limit = False
        
        # 与JS策略一致的日志格式
        print(f"当前持仓: {position_btc:.4f} BTC | 相对于开仓大小的倍数: {position_multiplier:.1f}x")
        
        # 根据持仓调整比例
        if position_multiplier >= max_multiplier:
            is_at_limit = True
            if position_btc > 0:
                print(f"⚠️ 多单已达上限({max_multiplier}x)，停止开多单")
                final_buy_ratio = Decimal('0')
                final_sell_ratio = Decimal('1')
            elif position_btc < 0:
                print(f"⚠️ 空单已达上限({max_multiplier}x)，停止开空单")
                final_buy_ratio = Decimal('1')
                final_sell_ratio = Decimal('0')
        elif position_multiplier > 0:
            # 使用position_multiplier来调整比例（与JS策略一致）
            reduction_ratio = position_multiplier / max_multiplier
            if position_btc > 0:
                buy_reduction = reduction_ratio * base_buy_ratio
                final_buy_ratio = max(Decimal('0'), base_buy_ratio - buy_reduction)
                final_sell_ratio = Decimal('1') - final_buy_ratio
                print(f"调整后比例: 卖单 {final_sell_ratio * 100:.0f}% / 买单 {final_buy_ratio * 100:.0f}%")
            elif position_btc < 0:
                sell_reduction = reduction_ratio * base_sell_ratio
                final_sell_ratio = max(Decimal('0'), base_sell_ratio - sell_reduction)
                final_buy_ratio = Decimal('1') - final_sell_ratio
                print(f"调整后比例: 卖单 {final_sell_ratio * 100:.0f}% / 买单 {final_buy_ratio * 100:.0f}%")
        
        if not is_at_limit:
            final_buy_ratio = max(Decimal('0.1'), min(Decimal('0.9'), final_buy_ratio))
            final_sell_ratio = max(Decimal('0.1'), min(Decimal('0.9'), final_sell_ratio))
        
        print(f"最终比例: 卖单 {final_sell_ratio * 100:.0f}% / 买单 {final_buy_ratio * 100:.0f}%")
        
        # 计算订单数量
        total_orders = cfg['TOTAL_ORDERS']
        sell_count = int(round(total_orders * float(final_sell_ratio)))
        buy_count = total_orders - sell_count
        
        # 计算理想价格
        # 卖单起始价格：使用ROUND_UP确保价格高于ask_price + SAFE_GAP，避免立即成交
        sell_start = ((ask_price + cfg['SAFE_GAP']) / interval).quantize(Decimal('1'), rounding=ROUND_UP) * interval
        # 确保卖单价格至少高于ask_price + SAFE_GAP
        if sell_start <= ask_price + cfg['SAFE_GAP']:
            sell_start += interval
        
        ideal_sell_prices = []
        for i in range(sell_count):
            price = sell_start + Decimal(i) * interval
            if price > mid_price + half_window + cfg['MAX_DRIFT_BUFFER']:
                break
            ideal_sell_prices.append(price)
        
        # 买单结束价格：使用ROUND_DOWN确保价格低于bid_price - SAFE_GAP，避免立即成交
        buy_end = ((bid_price - cfg['SAFE_GAP']) / interval).quantize(Decimal('1'), rounding=ROUND_DOWN) * interval
        # 确保买单价格至少低于bid_price - SAFE_GAP
        if buy_end >= bid_price - cfg['SAFE_GAP']:
            buy_end -= interval
        
        ideal_buy_prices = []
        for i in range(buy_count):
            price = buy_end - Decimal(i) * interval
            if price < mid_price - half_window - cfg['MAX_DRIFT_BUFFER']:
                break
            if price < cfg['MIN_VALID_PRICE']:
                break
            ideal_buy_prices.append(price)
        
        # 验证价格：确保买单价格严格低于当前买价，卖单价格严格高于当前卖价
        # 对于 post_only 订单，需要更大的安全边距（至少 SAFE_GAP）
        min_sell_price = ask_price + cfg['SAFE_GAP']
        max_buy_price = bid_price - cfg['SAFE_GAP']
        
        validated_sell_prices = [p for p in ideal_sell_prices if p >= min_sell_price]
        validated_buy_prices = [p for p in ideal_buy_prices if p <= max_buy_price]
        
        # 找出需要新下的订单
        ideal_prices_set = set(validated_sell_prices + validated_buy_prices)
        new_sell_prices = [p for p in validated_sell_prices if p not in existing_sell_orders]
        new_buy_prices = [p for p in validated_buy_prices if p not in existing_buy_orders]
        
        # 找出需要撤销的远单和重复订单
        # 使用去重后的价格数量来判断是否需要撤销（每个价格只需要一个订单）
        current_unique_prices = len(existing_sell_orders) + len(existing_buy_orders)
        # 使用实际订单数量来打印日志（反映真实情况）
        current_total_orders = all_sell_orders_count + all_buy_orders_count
        orders_to_cancel = []
        
        # 1. 清理重复订单：如果同一价格有多个订单，保留第一个，撤销多余的
        for price, orders_list in sell_orders_by_price.items():
            if len(orders_list) > 1:
                # 如果该价格在理想价格集合中，保留第一个，撤销多余的
                if price in ideal_prices_set:
                    # 保留第一个订单，撤销其余的
                    for order in orders_list[1:]:
                        orders_to_cancel.append({'type': 'sell', 'price': price, 'order_id': order.get('order_id')})
                        print(f"发现重复卖单 @ {price}，将撤销多余的订单 (订单ID: {order.get('order_id')})")
        
        for price, orders_list in buy_orders_by_price.items():
            if len(orders_list) > 1:
                # 如果该价格在理想价格集合中，保留第一个，撤销多余的
                if price in ideal_prices_set:
                    # 保留第一个订单，撤销其余的
                    for order in orders_list[1:]:
                        orders_to_cancel.append({'type': 'buy', 'price': price, 'order_id': order.get('order_id')})
                        print(f"发现重复买单 @ {price}，将撤销多余的订单 (订单ID: {order.get('order_id')})")
        
        # 2. 找出不在理想价格集合中的订单（远单）
        if (current_unique_prices > total_orders or 
            len(existing_sell_orders) > sell_count or 
            len(existing_buy_orders) > buy_count):
            
            # 找出不在理想价格集合中的订单
            far_sell_orders = [p for p in existing_sell_orders if p not in ideal_prices_set]
            far_buy_orders = [p for p in existing_buy_orders if p not in ideal_prices_set]
            
            # 将所有远单按距离中间价排序（从远到近）
            all_far = (
                [{'type': 'sell', 'price': p} for p in far_sell_orders] +
                [{'type': 'buy', 'price': p} for p in far_buy_orders]
            )
            
            # 计算距离阈值：不应该撤销距离当前价格太近的订单
            # 使用 SAFE_GAP 的倍数作为阈值，确保不会撤销可能很快成交的订单
            price_threshold = cfg['SAFE_GAP'] * Decimal('2')  # 至少是 SAFE_GAP 的2倍
            
            # 按距离中间价排序（从远到近），但过滤掉距离当前价格太近的订单
            all_far_with_distance = []
            for order in all_far:
                distance_from_mid = abs(order['price'] - mid_price)
                # 只考虑距离中间价足够远的订单（至少是 SAFE_GAP 的2倍）
                if distance_from_mid >= price_threshold:
                    all_far_with_distance.append((order, distance_from_mid))
            
            # 按距离从远到近排序
            all_far_with_distance.sort(key=lambda x: x[1], reverse=True)
            
            excess = current_unique_prices - total_orders
            # 只撤销距离足够远的订单
            for order, distance in all_far_with_distance:
                if len(orders_to_cancel) >= 10:
                    break
                if len(orders_to_cancel) >= excess:
                    break
                orders_to_cancel.append(order)
        
        print(f"中间价 ${mid_price:.1f} | 窗口 ±{half_window:.0f}")
        print(f"当前订单: {all_sell_orders_count}卖 + {all_buy_orders_count}买 = {current_total_orders} (去重后: {len(existing_sell_orders)}卖 + {len(existing_buy_orders)}买 = {current_unique_prices})")
        print(f"目标订单: {len(validated_sell_prices)}卖 + {len(validated_buy_prices)}买")
        print(f"需下单: {len(new_sell_prices)}卖 + {len(new_buy_prices)}买")
        if orders_to_cancel:
            cancel_info_list = []
            for o in orders_to_cancel:
                order_type_cn = '买' if o['type'] == 'buy' else '卖'
                cancel_info_list.append(f"{order_type_cn}-{o['price']}")
            cancel_info = ', '.join(cancel_info_list)
            print(f"需撤销: {len(orders_to_cancel)}单 → {cancel_info}")
        else:
            print("无需撤销订单")
        
        return {
            'sell_prices': new_sell_prices,
            'buy_prices': new_buy_prices,
            'cancel_orders': orders_to_cancel
        }
    
    def _get_position_info(self) -> Dict[str, Any]:
        """获取持仓信息（带超时保护）"""
        try:
            # 尝试从position_manager获取持仓
            # 注意：get_position 内部已经有错误处理，如果失败会返回空持仓
            position = self.position_manager.get_position(self.symbol)
            position_btc = Decimal(str(position.get('quantity', 0)))
            avg_price = Decimal(str(position.get('avg_price', 0)))
            unrealized_pnl = Decimal(str(position.get('unrealized_pnl', 0)))
            side = position.get('side', 'none')  # 持仓方向：long(多单), short(空单), none(无持仓)
        except Exception as e:
            # 如果获取持仓失败，使用默认值，不抛出异常
            error_msg = str(e)
            # 如果是超时错误，不频繁打印日志（已在position_manager中处理）
            if '超时' not in error_msg and 'timeout' not in error_msg.lower():
                print(f"获取持仓信息失败: {e}")
            position_btc = Decimal('0')
            avg_price = Decimal('0')
            unrealized_pnl = Decimal('0')
            side = 'none'
        
        return {
            'position_btc': position_btc,
            'avg_price': avg_price,
            'unrealized_pnl': unrealized_pnl,
            'side': side,  # 持仓方向
            'order_size': self.order_size
        }
    
    def _cancel_order_by_price(self, price: Decimal, order_type: str):
        """根据价格取消订单（带超时保护）"""
        try:
            # 获取订单列表（已经有缓存机制，应该很快）
            open_orders = self.order_manager.get_open_orders(self.symbol)
            order_type_cn = '买' if order_type.lower() == 'buy' else '卖'
            
            # 查找匹配的订单
            matching_orders = []
            for order in open_orders:
                order_price = Decimal(str(order.get('price', 0)))
                order_side = order.get('side', '').lower()
                
                if (order_price == price and 
                    order_side == order_type.lower()):
                    matching_orders.append(order)
            
            if not matching_orders:
                print(f"未找到匹配的订单 ({order_type_cn}单 @ {price})")
                return False
            
            # 取消第一个匹配的订单
            order = matching_orders[0]
            order_id = order.get('order_id')
            print(f"准备取消订单: {order_type_cn}单 @ {price} (订单ID: {order_id})")
            
            try:
                # 尝试取消订单，如果超时则跳过
                # 注意：cancel_order 内部已经有超时保护（60秒），如果超时会抛出异常
                self.order_manager.cancel_order(
                    symbol=self.symbol,
                    order_id=order_id
                )
                print(f"已取消订单: {order_type_cn}单 @ {price}")
                return True
            except Exception as cancel_error:
                # 如果取消订单失败（可能是超时），记录错误但继续
                error_msg = str(cancel_error)
                # 如果是超时错误，给出更明确的提示
                if '超时' in error_msg or 'timeout' in error_msg.lower():
                    print(f"取消订单超时 ({order_type_cn}单 @ {price})，跳过")
                else:
                    print(f"取消订单失败 ({order_type_cn}单 @ {price}): {cancel_error}")
                return False  # 返回False表示取消失败，但不抛出异常
        except Exception as e:
            print(f"获取订单列表失败: {e}")
            import traceback
            traceback.print_exc()
        return False
    
    def _execute_batch_orders(self, buy_prices: List[Decimal], sell_prices: List[Decimal]):
        """批量执行订单"""
        orders = (
            [{'type': 'buy', 'price': p} for p in buy_prices] +
            [{'type': 'sell', 'price': p} for p in sell_prices]
        )
        
        # 格式化订单列表为中文输出（与JS策略一致）
        orders_list = []
        for order in orders:
            order_type_cn = '买' if order['type'] == 'buy' else '卖'
            orders_list.append(f"{order_type_cn}-{order['price']}")
        print(f"新单: {', '.join(orders_list)}")
        for order in orders:
            try:
                # 检查订单冷却时间
                current_time = time.time()
                if current_time - self.last_order_time < self.order_cooldown:
                    wait_time = self.order_cooldown - (current_time - self.last_order_time)
                    time.sleep(wait_time)
                
                if order['type'] == 'buy':
                    result = self.order_manager.place_order(
                        symbol=self.symbol,
                        side='buy',
                        order_type='limit',
                        quantity=self.order_size,
                        price=order['price']
                    )
                else:
                    result = self.order_manager.place_order(
                        symbol=self.symbol,
                        side='sell',
                        order_type='limit',
                        quantity=self.order_size,
                        price=order['price']
                    )
                
                if result.get('order_id'):
                    self.last_order_time = time.time()
                    self.active_orders[result['order_id']] = result
                    # 订单提交成功，不打印日志（与JS策略一致）
                
                time.sleep(self.order_cooldown)
                
            except Exception as e:
                order_type_cn = '买' if order['type'] == 'buy' else '卖'
                print(f"下单失败 ({order_type_cn}单 @ {order['price']}): {e}")
        
        print('本轮下单完成')
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态（包含订单详细信息）"""
        try:
            ticker = self.order_manager.exchange.get_ticker(self.symbol)
            current_price = Decimal(str(ticker.get('price', 0))) if ticker else Decimal('0')
            bid_price = Decimal(str(ticker.get('bid', current_price))) if ticker else current_price
            ask_price = Decimal(str(ticker.get('ask', current_price))) if ticker else current_price
        except:
            current_price = Decimal('0')
            bid_price = Decimal('0')
            ask_price = Decimal('0')
        
        position_info = self._get_position_info()
        
        # 获取订单详细信息
        try:
            open_orders = self.order_manager.get_open_orders(self.symbol)
            sell_orders = []
            buy_orders = []
            
            for order in open_orders:
                order_price = order.get('price')
                order_side = order.get('side', '').lower()
                order_qty = order.get('quantity', '0')
                order_id = order.get('order_id', '')
                
                if order_price:
                    order_info = {
                        'order_id': order_id,
                        'price': str(order_price),
                        'quantity': str(order_qty)
                    }
                    if order_side == 'sell':
                        sell_orders.append(order_info)
                    elif order_side == 'buy':
                        buy_orders.append(order_info)
            
            # 按价格排序
            sell_orders.sort(key=lambda x: float(x['price']), reverse=False)  # 卖单从低到高
            buy_orders.sort(key=lambda x: float(x['price']), reverse=True)   # 买单从高到低
            
            # 统计实际订单数（包括所有有价格的未成交订单，不仅仅是策略自己创建的）
            total_active_orders = len(sell_orders) + len(buy_orders)
            
        except Exception as e:
            print(f"获取订单详细信息失败: {e}")
            sell_orders = []
            buy_orders = []
            total_active_orders = 0
        
        return {
            'is_running': self.is_running,
            'symbol': self.symbol,
            'order_size': str(self.order_size),
            'current_price': str(current_price),
            'bid_price': str(bid_price),
            'ask_price': str(ask_price),
            'cycle_count': self.cycle_count,
            'active_orders': total_active_orders,  # 使用实际查询到的订单数，而不是策略内部维护的订单数
            'sell_orders_count': len(sell_orders),
            'buy_orders_count': len(buy_orders),
            'sell_orders': sell_orders,  # 卖单列表（价格从低到高）
            'buy_orders': buy_orders,    # 买单列表（价格从高到低）
            'position_btc': str(position_info['position_btc']),
            'position_info': {
                'quantity': str(position_info['position_btc']),
                'avg_price': str(position_info.get('avg_price', '0')),
                'unrealized_pnl': str(position_info.get('unrealized_pnl', '0')),
                'side': position_info.get('side', 'none')  # 持仓方向：long(多单), short(空单), none(无持仓)
            },
            'config': {
                'total_orders': self.grid_config['TOTAL_ORDERS'],
                'window_percent': str(self.grid_config['WINDOW_PERCENT'] * 100) + '%',
                'sell_ratio': str(self.grid_config['SELL_RATIO'] * 100) + '%',
                'buy_ratio': str(self.grid_config['BUY_RATIO'] * 100) + '%',
                'base_price_interval': str(self.grid_config['BASE_PRICE_INTERVAL']),
                'safe_gap': str(self.grid_config['SAFE_GAP']),
                'max_drift_buffer': str(self.grid_config['MAX_DRIFT_BUFFER']),
                'min_valid_price': str(self.grid_config['MIN_VALID_PRICE']),
                'max_multiplier': str(self.grid_config['MAX_MULTIPLIER']),
                'order_cooldown': self.grid_config['ORDER_COOLDOWN'],
            }
        }

