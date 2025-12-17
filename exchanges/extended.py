"""
Extended交易所实现
基于jiaoyisuoshili/extended.py的Extended类
"""
import asyncio
import sys
import queue
import threading
import traceback
from typing import Dict, List, Optional, Any
from decimal import Decimal
from exchanges.base import BaseExchange
from exchanges.factory import ExchangeFactory

# 导入Extended交易所封装
try:
    import os
    # 添加jiaoyisuoshili目录到路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    jiaoyisuoshili_path = os.path.join(parent_dir, 'jiaoyisuoshili')
    if jiaoyisuoshili_path not in sys.path:
        sys.path.insert(0, jiaoyisuoshili_path)
    
    from extended import Extended
    # Extended的数据类型（可选导入）
    try:
        from extended import ExtendedTicker, ExtendedDepth, ExtendedOrder, ExtendedAccountSnapshot
    except ImportError:
        # 如果类型导入失败，不影响使用
        pass
    
    EXTENDED_AVAILABLE = True
except ImportError as e:
    print(f"警告: Extended交易所模块未找到: {e}")
    EXTENDED_AVAILABLE = False
    Extended = None


class ExtendedExchange(BaseExchange):
    """Extended交易所实现"""
    
    def __init__(self, api_key: str, secret_key: str, **kwargs):
        """
        初始化Extended交易所
        
        Args:
            api_key: API密钥
            secret_key: 私钥（Extended使用private_key作为secret_key）
            **kwargs:
                - private_key: 私钥（十六进制字符串，如果与secret_key不同）
                - public_key: 公钥（十六进制字符串，必填）
                - vault: 金库ID（必填）
                - testnet: 是否使用测试网（默认False）
                - default_market: 默认交易对（默认"BTC-USD"）
        """
        super().__init__(api_key, secret_key, **kwargs)
        
        if not EXTENDED_AVAILABLE:
            raise ImportError("Extended交易所模块未找到，请确保jiaoyisuoshili/extended.py存在")
        
        # Extended需要额外的参数
        private_key = kwargs.get('private_key', secret_key)
        public_key = kwargs.get('public_key')
        vault = kwargs.get('vault')
        testnet = kwargs.get('testnet', False)
        default_market = kwargs.get('default_market', 'BTC-USD')
        
        if not public_key:
            raise ValueError("Extended交易所需要提供public_key参数")
        if vault is None:
            raise ValueError("Extended交易所需要提供vault参数")
        
        # 创建Extended客户端
        self.extended_client = Extended(
            api_key=api_key,
            private_key=private_key,
            public_key=public_key,
            vault=vault,
            use_testnet=testnet,
            default_market=default_market
        )
        
        # 初始化标志
        self._initialized = False
        self._init_lock = asyncio.Lock()
        
        # 订单WebSocket订阅标志
        self._orders_subscribed = False
        
        # 持久的事件循环和线程，用于处理所有 API 调用
        self._api_loop: Optional[asyncio.AbstractEventLoop] = None
        self._api_thread: Optional[threading.Thread] = None
        self._api_loop_lock = threading.Lock()
        self._api_loop_initialized = False
        
        # 立即启动后台初始化（不阻塞）
        # 这样在第一次API调用时，初始化可能已经完成
        self._start_api_event_loop()
    
    def _ensure_initialized(self):
        """确保客户端已初始化（同步包装）"""
        # 注意：初始化检查移到_run_async中，确保在同一个事件循环中执行
        # 这里只做标记检查，不实际初始化
        pass
    
    def _start_api_event_loop(self):
        """启动持久的事件循环用于 API 调用"""
        # 检查属性是否存在
        if not hasattr(self, '_api_loop_lock'):
            return
        
        with self._api_loop_lock:
            if self._api_thread is not None and self._api_thread.is_alive():
                return  # 已经启动
            
            def run_api_loop():
                """在后台线程中运行持久的事件循环"""
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                self._api_loop = new_loop
                try:
                    # 在持久事件循环中初始化
                    async def init_in_loop():
                        try:
                            if not self._api_loop_initialized:
                                await self.extended_client.initialize()
                                self._api_loop_initialized = True
                                print(f"[Extended] 在持久事件循环中初始化成功")
                        except Exception as init_err:
                            print(f"[Extended] 在持久事件循环中初始化失败: {init_err}")
                            import traceback
                            traceback.print_exc()
                            # 即使初始化失败，也继续运行事件循环，后续调用可以重试
                    
                    # 先初始化
                    new_loop.run_until_complete(init_in_loop())
                    # 然后运行事件循环
                    new_loop.run_forever()
                except Exception as e:
                    print(f"[Extended] API事件循环错误: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    try:
                        new_loop.close()
                    except Exception:
                        pass
                    self._api_loop = None
                    self._api_loop_initialized = False
            
            self._api_thread = threading.Thread(target=run_api_loop, daemon=True)
            self._api_thread.start()
            # 等待事件循环启动
            import time
            time.sleep(0.5)
            print(f"[Extended] 已启动API事件循环线程")
    
    def _run_async(self, coro):
        """运行异步函数（同步包装）"""
        # 检查属性是否存在（防止在对象销毁时调用）
        if not hasattr(self, '_api_loop_lock'):
            # 如果属性不存在，直接使用回退方式（每次创建新事件循环）
            # 继续执行回退逻辑
            pass
        else:
            # 确保持久事件循环已启动
            if not hasattr(self, '_api_loop') or self._api_loop is None or not self._api_loop.is_running():
                self._start_api_event_loop()
                # 等待事件循环启动
                import time
                max_wait = 10
                waited = 0
                while (not hasattr(self, '_api_loop') or self._api_loop is None or not self._api_loop.is_running()) and waited < max_wait:
                    time.sleep(0.1)
                    waited += 0.1
            
            # 如果持久事件循环可用，使用它
            if hasattr(self, '_api_loop') and self._api_loop is not None and self._api_loop.is_running():
                result_queue = queue.Queue()
                
                def run_in_persistent_loop():
                    """在持久事件循环中运行异步代码"""
                    try:
                        # 确保在持久事件循环中已初始化
                        # 如果还没有初始化，先初始化
                        if not getattr(self, '_api_loop_initialized', False):
                            async def ensure_init():
                                if not getattr(self, '_api_loop_initialized', False):
                                    await self.extended_client.initialize()
                                    self._api_loop_initialized = True
                            
                            init_future = asyncio.run_coroutine_threadsafe(ensure_init(), self._api_loop)
                            # Extended 在主网上初始化可能比较慢，这里适当放宽超时时间，
                            # 避免因为 10 秒超时导致后续每次首次调用都拿不到真实数据。
                            init_future.result(timeout=60)  # 最长等待 60 秒完成初始化
                        
                        # 使用持久的事件循环运行异步操作
                        future = asyncio.run_coroutine_threadsafe(coro, self._api_loop)
                        result = future.result(timeout=60)  # 60秒超时
                        result_queue.put(('success', result))
                    except Exception as e:
                        error_info = {
                            'error': str(e),
                            'type': type(e).__name__,
                            'traceback': traceback.format_exc()
                        }
                        result_queue.put(('error', error_info))
                
                thread = threading.Thread(target=run_in_persistent_loop, daemon=True)
                thread.start()
                thread.join(timeout=65)  # 比 future.result 的超时时间稍长
                
                if not result_queue.empty():
                    status, result = result_queue.get()
                    if status == 'error':
                        # 处理错误信息
                        if isinstance(result, dict):
                            error_msg = result.get('error', '异步操作失败')
                            error_type = result.get('type', '')
                            
                            traceback_str = result.get('traceback', '')
                            if 'Event loop is closed' in error_msg or 'loop' in error_msg.lower():
                                full_error = f"事件循环错误: {error_msg}\n类型: {error_type}\n{traceback_str}"
                                raise RuntimeError(full_error)
                            elif 'Connection' in error_type or 'timeout' in error_msg.lower() or 'Connector is closed' in error_msg:
                                full_error = f"网络连接失败: {error_msg}\n类型: {error_type}\n{traceback_str}"
                                raise ConnectionError(full_error)
                            elif '初始化' in error_msg or 'initialization' in error_msg.lower():
                                full_error = f"初始化失败: {error_msg}\n类型: {error_type}\n{traceback_str}"
                                raise RuntimeError(full_error)
                            else:
                                # 将异常类型和traceback一起带上，避免只有“操作失败:”这类空信息
                                full_error = f"操作失败: {error_msg}\n类型: {error_type}\n{traceback_str}"
                                raise RuntimeError(full_error)
                        else:
                            raise result
                    return result
                else:
                    if thread.is_alive():
                        raise RuntimeError("异步操作超时（65秒），线程仍在运行中")
                    else:
                        raise RuntimeError("异步操作超时（65秒），线程已退出")
        
        # 回退到原来的方式（每次创建新事件循环）
        result_queue = queue.Queue()
        
        def run_in_thread():
            """在线程中运行异步代码"""
            # 总是创建新的事件循环（在线程中）
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                # 在同一个事件循环中先初始化（如果需要）
                # 注意：只在真正需要时初始化，不要每次都重新初始化
                try:
                    # 检查是否已初始化（通过检查trading_client和_initialized标志）
                    needs_init = (
                        not hasattr(self.extended_client, 'trading_client') or
                        self.extended_client.trading_client is None or
                        not getattr(self.extended_client, '_initialized', False)
                    )
                    
                    # 只在真正需要时初始化，不要每次都重新初始化
                    # 这样可以避免关闭和重新创建 session，导致 "Connector is closed" 错误
                    if needs_init:
                        # 在新的事件循环中初始化（使用任务包装）
                        async def init_task():
                            await self.extended_client.initialize()
                        init_coro_task = new_loop.create_task(init_task())
                        new_loop.run_until_complete(init_coro_task)
                        
                        # 验证初始化是否成功
                        if not getattr(self.extended_client, '_initialized', False):
                            raise RuntimeError("初始化后_initialized标志未设置")
                        if not hasattr(self.extended_client, 'trading_client') or self.extended_client.trading_client is None:
                            raise RuntimeError("初始化后trading_client仍为None")
                    else:
                        # 如果已经初始化，确保 trading_client 的 session 绑定到当前事件循环
                        # 通过调用一个简单的 API 来触发 session 创建/绑定
                        async def ensure_session():
                            """确保 session 已创建并绑定到当前事件循环"""
                            if hasattr(self.extended_client, 'trading_client') and self.extended_client.trading_client:
                                try:
                                    # 尝试获取 session，这会确保它绑定到当前事件循环
                                    await self.extended_client.trading_client.account.get_session()
                                except Exception:
                                    pass  # 如果获取失败，继续执行
                        
                        try:
                            ensure_session_task = new_loop.create_task(ensure_session())
                            new_loop.run_until_complete(ensure_session_task)
                        except Exception:
                            pass  # 如果失败，继续执行（可能 session 已经存在）
                            
                except Exception as init_error:
                    # 如果初始化失败，尝试重新初始化
                    error_msg = str(init_error).lower()
                    if "already" not in error_msg and "initialized" not in error_msg:
                        # 尝试重置并重新初始化
                        try:
                            # 重置初始化状态
                            if hasattr(self.extended_client, '_initialized'):
                                self.extended_client._initialized = False
                            if hasattr(self.extended_client, 'trading_client'):
                                self.extended_client.trading_client = None
                            
                            # 使用任务包装重新初始化
                            async def retry_init_task():
                                await self.extended_client.initialize()
                            retry_init_coro_task = new_loop.create_task(retry_init_task())
                            new_loop.run_until_complete(retry_init_coro_task)
                            
                            # 再次验证初始化是否成功
                            if not getattr(self.extended_client, '_initialized', False):
                                raise RuntimeError("重试初始化后_initialized标志未设置")
                            if not hasattr(self.extended_client, 'trading_client') or self.extended_client.trading_client is None:
                                raise RuntimeError("重试初始化后trading_client仍为None")
                                
                        except Exception as retry_error:
                            error_info = {
                                'error': f"初始化失败: {str(retry_error)}",
                                'type': type(retry_error).__name__,
                                'traceback': traceback.format_exc()
                            }
                            result_queue.put(('error', error_info))
                            return
                    else:
                        # 如果错误信息包含"already"或"initialized"，可能是初始化已经完成
                        # 验证一下是否真的已初始化
                        if not getattr(self.extended_client, '_initialized', False):
                            error_info = {
                                'error': f"初始化检查失败: {str(init_error)}",
                                'type': type(init_error).__name__,
                                'traceback': traceback.format_exc()
                            }
                            result_queue.put(('error', error_info))
                            return
                
                # 运行实际的异步操作
                # 对于 Python 3.11+，asyncio.timeout() 必须在任务中运行
                # 使用 create_task 确保 timeout context manager 可以正常工作
                async def run_with_timeout():
                    """包装异步操作，确保 timeout context manager 可以正常工作"""
                    # 确保在任务上下文中运行，这样 SDK 内部的 asyncio.timeout() 可以正常工作
                    return await coro
                
                # 创建任务并运行
                task = new_loop.create_task(run_with_timeout())
                result = new_loop.run_until_complete(task)
                result_queue.put(('success', result))
            except Exception as e:
                # 传递详细的错误信息
                error_info = {
                    'error': str(e),
                    'type': type(e).__name__,
                    'traceback': traceback.format_exc()
                }
                result_queue.put(('error', error_info))
            finally:
                # 清理事件循环
                # 注意：不要关闭 trading_client 的 session，因为它是共享的，关闭后会影响后续调用
                # session 会在 trading_client 的生命周期内保持打开状态
                try:
                    # 取消所有待处理的任务
                    pending = asyncio.all_tasks(new_loop)
                    for task in pending:
                        if not task.done():
                            task.cancel()
                    # 等待任务取消完成
                    if pending:
                        new_loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass
                # 关闭事件循环
                try:
                    new_loop.close()
                except Exception:
                    pass
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        thread.join(timeout=60)  # 增加超时时间到60秒，避免取消订单等操作超时
        
        if not result_queue.empty():
            status, result = result_queue.get()
            if status == 'error':
                # 处理错误信息
                if isinstance(result, dict):
                    error_msg = result.get('error', '异步操作失败')
                    error_type = result.get('type', '')
                    
                    # 根据错误类型提供友好的错误信息
                    traceback_str = result.get('traceback', '')
                    if 'Event loop is closed' in error_msg or 'loop' in error_msg.lower():
                        full_error = f"事件循环错误: {error_msg}\n类型: {error_type}\n{traceback_str}"
                        raise RuntimeError(full_error)
                    elif 'Connection' in error_type or 'timeout' in error_msg.lower():
                        full_error = f"网络连接失败: {error_msg}\n类型: {error_type}\n{traceback_str}"
                        raise ConnectionError(full_error)
                    elif '初始化' in error_msg or 'initialization' in error_msg.lower():
                        full_error = f"初始化失败: {error_msg}\n类型: {error_type}\n{traceback_str}"
                        raise RuntimeError(full_error)
                    else:
                        full_error = f"操作失败: {error_msg}\n类型: {error_type}\n{traceback_str}"
                        raise RuntimeError(full_error)
                else:
                    raise result
            return result
        else:
            # 检查线程是否还在运行
            if thread.is_alive():
                raise RuntimeError("异步操作超时（60秒），线程仍在运行中")
            else:
                raise RuntimeError("异步操作超时（60秒），线程已退出")
    
    def normalize_symbol(self, symbol: str) -> str:
        """Extended交易对标准化（如 BTC/USDT -> BTC-USD）"""
        # Extended使用BTC-USD格式，而不是BTC/USDT
        symbol = symbol.replace('/', '-').upper()
        # 如果包含USDT，转换为USD
        if symbol.endswith('-USDT'):
            symbol = symbol.replace('-USDT', '-USD')
        return symbol
    
    def get_balance(self, currency: Optional[str] = None) -> Dict[str, Any]:
        """获取账户余额（基于 account 快照，和旧实现保持一致）
        
        逻辑：
        - 直接复用 `extended_client.get_account()` 的结果，这个方法在
          `jiaoyisuoshili/extended.py` 中已经验证可以正确返回余额和持仓快照。
        - 优先从 `account.assets` 中取第一个资产作为总资产显示。
        """

        async def _get_balance():
            account = await self.extended_client.get_account()

            # 如果指定了币种，则按币种查找
            if currency:
                for asset in getattr(account, "assets", []) or []:
                    if asset.asset.upper() == currency.upper():
                        return {
                            "currency": asset.asset,
                            "available": asset.available_balance,
                            "frozen": str(
                                Decimal(asset.wallet_balance) - Decimal(asset.available_balance)
                            ),
                            "total": asset.wallet_balance,
                        }
                # 未找到该币种，返回 0
                return {
                    "currency": currency,
                    "available": "0.0",
                    "frozen": "0.0",
                    "total": "0.0",
                }

            # 未指定币种：取第一个资产作为总资产
            assets = getattr(account, "assets", []) or []
            if assets:
                main_asset = assets[0]
                return {
                    "currency": main_asset.asset,
                    "available": main_asset.available_balance,
                    "frozen": str(
                        Decimal(main_asset.wallet_balance) - Decimal(main_asset.available_balance)
                    ),
                    "total": main_asset.wallet_balance,
                }

            # 如果没有资产列表，退回到账户快照的总余额字段
            return {
                "currency": "all",
                "available": account.available_balance,
                "frozen": str(
                    Decimal(account.total_wallet_balance) - Decimal(account.available_balance)
                ),
                "total": account.total_wallet_balance,
            }

        # 正常情况下应返回真实余额；如果极端情况下 _run_async 失败，仍然兜底为 0，
        # 但这时会在终端看到具体异常，便于排查。
        coro = _get_balance()
        try:
            return self._run_async(coro)
        except Exception as e:
            try:
                coro.close()
            except Exception:
                pass
            print(f"[Extended] get_balance 通过 account 快照获取余额失败: {e}")
            return {
                "currency": currency or "all",
                "available": "0.0",
                "frozen": "0.0",
                "total": "0.0",
            }
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取交易对价格信息（包含买1和卖1价格，优先使用WebSocket）
        
        要求：
        - 不能把底层 SDK / 网络异常直接抛到上层，否则例如启动策略时会因为
          获取 ticker 失败而导致接口 500。
        - 要避免协程在 `_run_async` 之前就被丢弃，产生
          "coroutine ... was never awaited" 的 RuntimeWarning。
        """
        normalized_symbol = self.normalize_symbol(symbol)
        
        async def _get_ticker():
            try:
                # 获取 ticker 数据
                ticker = await self.extended_client.get_ticker(normalized_symbol)
            except Exception as e:
                # 获取 ticker 失败时，记录日志并返回一个安全的默认值
                print(f"[Extended] 获取 ticker 失败: {e}")
                import traceback
                traceback.print_exc()
                return {
                    'symbol': normalized_symbol,
                    'price': '0',
                    'bid': '0',
                    'ask': '0',
                    'bid_qty': '0',
                    'ask_qty': '0',
                    'high': '0',
                    'low': '0',
                    'volume': '0',
                    'quote_volume': '0',
                    'price_change': '0',
                    'price_change_percent': '0',
                }
            
            # 默认使用 last_price
            bid_price = ticker.last_price
            ask_price = ticker.last_price
            bid_qty = '0'
            ask_qty = '0'
            
            # 获取订单簿以获取买1和卖1价格（优先使用 WebSocket）
            try:
                depth = await self.extended_client.get_depth(normalized_symbol, limit=1)
                
                if depth.bids and len(depth.bids) > 0:
                    bid_price = depth.bids[0].price
                    bid_qty = depth.bids[0].quantity
                if depth.asks and len(depth.asks) > 0:
                    ask_price = depth.asks[0].price
                    ask_qty = depth.asks[0].quantity
            except Exception as e:
                # 如果订单簿获取失败，使用 ticker 的 last_price 作为 fallback
                print(f"[Extended] 获取订单簿失败，使用 last_price 作为买1/卖1价格: {e}")
                import traceback
                traceback.print_exc()
            
            return {
                'symbol': normalized_symbol,
                'price': ticker.last_price,
                'bid': bid_price,  # 买1价格
                'ask': ask_price,  # 卖1价格
                'bid_qty': bid_qty,
                'ask_qty': ask_qty,
                'high': ticker.high_price,
                'low': ticker.low_price,
                'volume': ticker.volume,
                'quote_volume': ticker.quote_volume,
                'price_change': ticker.price_change or '0',
                'price_change_percent': ticker.price_change_percent or '0'
            }
        
        coro = _get_ticker()
        try:
            return self._run_async(coro)
        except Exception as e:
            # 如果在 _run_async 内部出错，关闭协程并返回安全默认值，避免 500
            try:
                coro.close()
            except Exception:
                pass
            print(f"[Extended] _run_async 执行 get_ticker 失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'symbol': normalized_symbol,
                'price': '0',
                'bid': '0',
                'ask': '0',
                'bid_qty': '0',
                'ask_qty': '0',
                'high': '0',
                'low': '0',
                'volume': '0',
                'quote_volume': '0',
                'price_change': '0',
                'price_change_percent': '0',
            }
    
    def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """获取订单簿"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        async def _get_orderbook():
            depth = await self.extended_client.get_depth(normalized_symbol, limit)
            
            bids = [[bid.price, bid.quantity] for bid in depth.bids[:limit]]
            asks = [[ask.price, ask.quantity] for ask in depth.asks[:limit]]
            
            return {
                'symbol': normalized_symbol,
                'bids': bids,
                'asks': asks,
                'last_update_id': depth.last_update_id
            }
        
        return self._run_async(_get_orderbook())
    
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
        """下单"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        if order_type == 'limit' and price is None:
            raise ValueError("限价单必须指定价格")
        
        async def _place_order():
            # 转换side格式（buy/sell -> BUY/SELL）
            side_upper = side.upper()
            if side_upper not in ['BUY', 'SELL']:
                raise ValueError(f"不支持的订单方向: {side}")
            
            # 转换order_type格式
            order_type_upper = order_type.upper()
            if order_type_upper not in ['LIMIT', 'MARKET']:
                raise ValueError(f"不支持的订单类型: {order_type}")
            
            # 对于限价单，如果没有明确指定postOnly，默认设置为True（确保挂单而不是立即成交）
            if order_type_upper == 'LIMIT' and 'postOnly' not in kwargs and 'post_only' not in kwargs:
                kwargs['postOnly'] = True
            
            # 如果传入了post_only参数，也传递到kwargs
            if post_only:
                kwargs['postOnly'] = True
            
            # 创建订单
            order = await self.extended_client.create_order(
                symbol=normalized_symbol,
                side=side_upper,
                order_type=order_type_upper,
                quantity=float(quantity),
                price=float(price) if price else None,
                params=kwargs
            )
            
            return {
                'order_id': str(order.order_id),
                'symbol': normalized_symbol,
                'side': order.side.lower(),
                'type': order.type.lower(),
                'quantity': order.quantity,
                'price': order.price if order.price != "0" else None,
                'status': order.status,
                'time_in_force': order.time_in_force,
                'executed_qty': order.executed_qty,
                'avg_price': order.avg_price,
                'time': order.time,
                'update_time': order.update_time
            }
        
        return self._run_async(_place_order())
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """取消订单"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        async def _cancel_order():
            try:
                order_id_int = int(order_id)
            except ValueError:
                # 如果不是数字，尝试通过client_order_id取消
                order = await self.extended_client.cancel_order(
                    symbol=normalized_symbol,
                    client_order_id=order_id
                )
                return {
                    'order_id': str(order.order_id),
                    'symbol': normalized_symbol,
                    'status': 'CANCELED'
                }
            
            order = await self.extended_client.cancel_order(
                symbol=normalized_symbol,
                order_id=order_id_int
            )
            
            return {
                'order_id': str(order.order_id),
                'symbol': normalized_symbol,
                'status': 'CANCELED'
            }
        
        return self._run_async(_cancel_order())
    
    def get_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """查询订单"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        async def _get_order():
            # 先获取所有未成交订单
            open_orders = await self.extended_client.get_open_orders(normalized_symbol)
            
            # 查找指定订单
            try:
                order_id_int = int(order_id)
            except ValueError:
                # 通过client_order_id查找
                for order in open_orders:
                    if order.client_order_id == order_id:
                        # side和type已经是字符串（从_format_order中通过.value获取）
                        side_str = order.side.lower() if isinstance(order.side, str) else str(order.side).lower()
                        type_str = order.type.lower() if isinstance(order.type, str) else str(order.type).lower()
                        return {
                            'order_id': str(order.order_id),
                            'client_order_id': order.client_order_id,
                            'symbol': normalized_symbol,
                            'side': side_str,
                            'type': type_str,
                            'quantity': order.quantity,
                            'price': order.price if order.price != "0" else None,
                            'status': order.status,
                            'executed_qty': order.executed_qty,
                            'avg_price': order.avg_price,
                            'time': order.time,
                            'update_time': order.update_time
                        }
            else:
                # 通过order_id查找
                for order in open_orders:
                    if order.order_id == order_id_int:
                        # side和type已经是字符串（从_format_order中通过.value获取）
                        side_str = order.side.lower() if isinstance(order.side, str) else str(order.side).lower()
                        type_str = order.type.lower() if isinstance(order.type, str) else str(order.type).lower()
                        return {
                            'order_id': str(order.order_id),
                            'client_order_id': order.client_order_id,
                            'symbol': normalized_symbol,
                            'side': side_str,
                            'type': type_str,
                            'quantity': order.quantity,
                            'price': order.price if order.price != "0" else None,
                            'status': order.status,
                            'executed_qty': order.executed_qty,
                            'avg_price': order.avg_price,
                            'time': order.time,
                            'update_time': order.update_time
                        }
            
            # 如果未找到，返回未知状态
            return {
                'order_id': order_id,
                'symbol': normalized_symbol,
                'status': 'UNKNOWN',
                'message': '订单未找到或已成交'
            }
        
        return self._run_async(_get_order())
    
    def get_open_orders(self, symbol: Optional[str] = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        获取未成交订单列表（优先使用缓存，避免API限速）
        
        Args:
            symbol: 交易对符号，None表示获取所有交易对的订单
            use_cache: 是否使用缓存，如果缓存有效且在TTL内，直接返回缓存数据
        
        Returns:
            未成交订单列表
        """
        
        # 启动订单WebSocket订阅（如果还没有启动）
        if not self._orders_subscribed:
            try:
                # 注册订单更新回调（这会启动后台轮询）
                def on_orders_update(orders):
                    """订单更新回调（用于保持缓存最新）"""
                    pass  # 缓存已在get_open_orders中更新
                
                self.extended_client.watch_order(on_orders_update)
                self._orders_subscribed = True
                print(f"[Extended] 已启动订单WebSocket订阅（后台轮询，每5秒更新一次）")
            except Exception as e:
                print(f"[Extended] 启动订单订阅失败: {e}，将使用REST API")
        
        async def _get_open_orders():
            # 优先使用缓存（如果启用）
            if symbol:
                normalized_symbol = self.normalize_symbol(symbol)
                orders = await self.extended_client.get_open_orders(normalized_symbol, use_cache=use_cache)
            else:
                # 获取所有交易对的订单
                # 如果使用缓存，直接从缓存获取
                if use_cache:
                    import time
                    current_time = time.time()
                    cache_valid = (
                        self.extended_client.orders_cache_timestamp > 0 and
                        (current_time - self.extended_client.orders_cache_timestamp) < self.extended_client.orders_cache_ttl
                    )
                    
                    if cache_valid:
                        # 从缓存获取所有订单
                        with self.extended_client.lock:
                            all_orders = list(self.extended_client.open_orders.values())
                        # 只返回未成交订单
                        orders = [order for order in all_orders if order.status in ['NEW', 'PARTIALLY_FILLED']]
                    else:
                        # 缓存无效，使用REST API
                        markets = await self.extended_client.get_markets()
                        all_orders = []
                        for market_symbol in markets.keys():
                            try:
                                market_orders = await self.extended_client.get_open_orders(market_symbol, use_cache=False)
                                all_orders.extend(market_orders)
                            except Exception:
                                continue
                        orders = all_orders
                else:
                    # 不使用缓存，直接使用REST API
                    markets = await self.extended_client.get_markets()
                    all_orders = []
                    for market_symbol in markets.keys():
                        try:
                            market_orders = await self.extended_client.get_open_orders(market_symbol, use_cache=False)
                            all_orders.extend(market_orders)
                        except Exception:
                            continue
                    orders = all_orders
            
            result = []
            for order in orders:
                # side和type已经是字符串（从_format_order中通过.value获取）
                side_str = order.side.lower() if isinstance(order.side, str) else str(order.side).lower()
                type_str = order.type.lower() if isinstance(order.type, str) else str(order.type).lower()
                result.append({
                    'order_id': str(order.order_id),
                    'client_order_id': order.client_order_id,
                    'symbol': order.symbol,
                    'side': side_str,
                    'type': type_str,
                    'quantity': order.quantity,
                    'price': order.price if order.price != "0" else None,
                    'status': order.status,
                    'executed_qty': order.executed_qty,
                    'avg_price': order.avg_price,
                    'time': order.time,
                    'update_time': order.update_time
                })
            
            return result
        
        return self._run_async(_get_open_orders())
    
    def get_position(self, symbol: str) -> Dict[str, Any]:
        """获取持仓信息"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        async def _get_position():
            try:
                positions = await self.extended_client.get_positions(normalized_symbol)
                if positions and len(positions) > 0:
                    position = positions[0]
                    # 解析持仓数量
                    position_amt_str = str(position.position_amt)
                    position_amt = Decimal(position_amt_str)
                    entry_price = Decimal(str(position.entry_price)) if position.entry_price else Decimal('0')
                    unrealized_pnl = Decimal(str(position.unrealized_profit)) if position.unrealized_profit else Decimal('0')
                    
                    # 优先使用 position_side 字段判断方向（Extended交易所使用此字段）
                    # 如果 position_side 不可用，再根据 position_amt 的正负判断
                    position_side = getattr(position, 'position_side', None)
                    if position_side:
                        position_side_upper = str(position_side).upper()
                        if position_side_upper == 'LONG':
                            side = 'long'  # 多单
                        elif position_side_upper == 'SHORT':
                            side = 'short'  # 空单
                        else:
                            # 如果 position_side 不是 LONG 或 SHORT，根据 position_amt 判断
                            if position_amt > 0:
                                side = 'long'
                            elif position_amt < 0:
                                side = 'short'
                            else:
                                side = 'none'
                    else:
                        # 如果没有 position_side 字段，根据持仓数量判断方向：正数为多单，负数为空单
                        if position_amt > 0:
                            side = 'long'  # 多单
                        elif position_amt < 0:
                            side = 'short'  # 空单
                        else:
                            side = 'none'  # 无持仓
                    
                    # 如果判断为空单，但 position_amt 为正数，需要将 quantity 转为负数
                    # 这样前端显示时会更直观
                    if side == 'short' and position_amt > 0:
                        position_amt = -position_amt
                    
                    return {
                        'symbol': normalized_symbol,
                        'quantity': position_amt,
                        'avg_price': entry_price,
                        'unrealized_pnl': unrealized_pnl,
                        'side': side,  # 持仓方向：long(多单), short(空单), none(无持仓)
                        'leverage': str(position.leverage) if hasattr(position, 'leverage') else '1',
                        'position_side': position.position_side if hasattr(position, 'position_side') else 'BOTH'
                    }
                else:
                    # 没有持仓
                    return {
                        'symbol': normalized_symbol,
                        'quantity': Decimal('0'),
                        'avg_price': Decimal('0'),
                        'unrealized_pnl': Decimal('0'),
                        'side': 'none'  # 无持仓
                    }
            except Exception as e:
                print(f"获取持仓失败: {e}")
                # 出错时返回空持仓
                return {
                    'symbol': normalized_symbol,
                    'quantity': Decimal('0'),
                    'avg_price': Decimal('0'),
                    'unrealized_pnl': Decimal('0')
                }
        
        return self._run_async(_get_position())
    
    def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取K线数据"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        # Extended暂不支持K线数据，返回空列表或使用Ticker数据模拟
        # 这里返回空列表，实际使用时可以通过其他方式获取
        return []
    
    def close(self):
        """关闭客户端连接"""
        try:
            # 关闭持久事件循环
            if hasattr(self, '_api_loop') and self._api_loop is not None and self._api_loop.is_running():
                try:
                    # 停止事件循环
                    self._api_loop.call_soon_threadsafe(self._api_loop.stop)
                    # 等待线程结束
                    if hasattr(self, '_api_thread') and self._api_thread is not None:
                        self._api_thread.join(timeout=2)
                except Exception as e:
                    print(f"[Extended] 关闭API事件循环时出错: {e}")
            
            # 关闭Extended客户端
            if hasattr(self, 'extended_client') and self.extended_client:
                async def _close():
                    await self.extended_client.close()
                
                try:
                    self._run_async(_close())
                except Exception as e:
                    print(f"关闭Extended客户端时出错: {e}")
        except Exception as e:
            # 如果关闭过程中出错，只记录错误，不抛出异常
            print(f"关闭Extended交易所时出错: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            self.close()
        except Exception:
            pass


# 注册Extended交易所
ExchangeFactory.register('extended', ExtendedExchange)

