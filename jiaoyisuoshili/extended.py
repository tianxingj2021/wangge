"""
Extended交易所API封装
基于官方x10-python-trading-starknet SDK
"""
import time
import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime, timedelta

# 导入Extended官方SDK
try:
    from x10.perpetual.accounts import StarkPerpetualAccount
    from x10.perpetual.configuration import TESTNET_CONFIG, MAINNET_CONFIG
    from x10.perpetual.trading_client import PerpetualTradingClient
    from x10.perpetual.orders import OrderSide, OrderType, OrderStatus, TimeInForce
    from x10.perpetual.positions import PositionModel, PositionSide
    from x10.perpetual.balances import BalanceModel
    from x10.perpetual.markets import MarketModel, MarketStatsModel
    from x10.perpetual.orderbook import OrderBook
    from x10.utils.model import X10BaseModel
    X10_AVAILABLE = True
except ImportError as e:
    print(f"警告: Extended SDK未安装，请运行: pip install x10-python-trading-starknet")
    print(f"导入错误: {e}")
    X10_AVAILABLE = False
    
    # 定义占位符类
    class StarkPerpetualAccount:
        pass
    class PerpetualTradingClient:
        pass
    class OrderSide:
        BUY = "BUY"
        SELL = "SELL"
    class OrderType:
        LIMIT = "LIMIT"
        MARKET = "MARKET"
        CONDITIONAL = "CONDITIONAL"
    class OrderStatus:
        NEW = "NEW"
        FILLED = "FILLED"
        CANCELLED = "CANCELLED"
    class TimeInForce:
        GTT = "GTT"
        IOC = "IOC"
        FOK = "FOK"
    class PositionModel:
        pass
    class PositionSide:
        LONG = "LONG"
        SHORT = "SHORT"
    class BalanceModel:
        pass
    class MarketModel:
        pass
    class MarketStatsModel:
        pass
    class OrderBook:
        pass
    class X10BaseModel:
        pass
    
    # 配置占位符
    TESTNET_CONFIG = None
    MAINNET_CONFIG = None


@dataclass
class ExtendedDepthLevel:
    price: str
    quantity: str


@dataclass
class ExtendedDepth:
    symbol: str
    last_update_id: int
    bids: List[ExtendedDepthLevel]
    asks: List[ExtendedDepthLevel]
    event_time: Optional[int] = None


@dataclass
class ExtendedTicker:
    symbol: str
    last_price: str
    open_price: str
    high_price: str
    low_price: str
    volume: str
    quote_volume: str
    price_change: Optional[str] = None
    price_change_percent: Optional[str] = None
    event_time: Optional[int] = None


@dataclass
class ExtendedKline:
    open_time: int
    open: str
    high: str
    low: str
    close: str
    volume: str
    close_time: int
    quote_asset_volume: str
    number_of_trades: int
    taker_buy_base_asset_volume: str
    taker_buy_quote_asset_volume: str
    event_time: Optional[int] = None


@dataclass
class ExtendedOrder:
    order_id: int
    client_order_id: str
    symbol: str
    side: str
    type: str
    quantity: str
    price: str
    stop_price: Optional[str] = None
    reduce_only: bool = False
    close_position: bool = False
    status: str = "NEW"
    time_in_force: str = "GTC"
    executed_qty: str = "0"
    cum_quote: str = "0"
    avg_price: str = "0"
    time: int = 0
    update_time: int = 0
    working_type: str = "CONTRACT_PRICE"
    price_protect: bool = False
    activation_price: Optional[str] = None
    price_rate: Optional[str] = None
    realized_pnl: Optional[str] = None


@dataclass
class ExtendedAccountPosition:
    symbol: str
    position_amt: str
    entry_price: str
    unrealized_profit: str
    leverage: str
    isolated: bool = False
    position_side: str = "BOTH"
    update_time: int = 0


@dataclass
class ExtendedAccountAsset:
    asset: str
    wallet_balance: str
    unrealized_profit: str
    margin_balance: str
    maint_margin: str
    initial_margin: str
    position_initial_margin: str
    open_order_initial_margin: str
    cross_wallet_balance: str
    cross_un_pnl: str
    available_balance: str
    max_withdraw_amount: str
    margin_available: bool = True
    update_time: int = 0


@dataclass
class ExtendedAccountSnapshot:
    fee_tier: int
    can_trade: bool
    can_deposit: bool
    can_withdraw: bool
    update_time: int
    total_initial_margin: str
    total_maint_margin: str
    total_wallet_balance: str
    total_unrealized_profit: str
    total_margin_balance: str
    total_position_initial_margin: str
    total_open_order_initial_margin: str
    total_cross_wallet_balance: str
    total_cross_un_pnl: str
    available_balance: str
    max_withdraw_amount: str
    assets: List[ExtendedAccountAsset]
    positions: List[ExtendedAccountPosition]


class Extended:
    """Extended交易所API封装"""
    
    def __init__(self, api_key: str, private_key: str, public_key: str, vault: int, 
                 use_testnet: bool = False, default_market: str = "BTC-USD"):
        """
        初始化Extended交易所客户端
        
        Args:
            api_key: API密钥
            private_key: 私钥（十六进制字符串）
            public_key: 公钥（十六进制字符串）
            vault: 金库ID
            use_testnet: 是否使用测试网
            default_market: 默认交易对
        """
        if not X10_AVAILABLE:
            raise ImportError("Extended SDK未安装，请运行: pip install x10-python-trading-starknet")
        
        # 检查必要的参数
        if not api_key or not private_key or not public_key:
            raise ValueError("Extended交易所需要提供api_key、private_key和public_key")
        
        self.api_key = api_key
        self.private_key = private_key
        self.public_key = public_key
        self.vault = vault
        self.use_testnet = use_testnet
        self.default_market = default_market
        
        # 选择配置
        self.config = TESTNET_CONFIG if use_testnet else MAINNET_CONFIG
        print(f"[Extended] 使用{'测试网' if use_testnet else '主网'}配置")
        
        # 创建Stark账户
        self.stark_account = StarkPerpetualAccount(
            vault=vault,
            private_key=private_key,
            public_key=public_key,
            api_key=api_key
        )
        
        # 交易客户端
        self.trading_client: Optional[PerpetualTradingClient] = None
        
        # 回调函数
        self.account_callbacks: List[Callable] = []
        self.order_callbacks: List[Callable] = []
        self.depth_callbacks: Dict[str, List[Callable]] = {}
        self.ticker_callbacks: List[Callable] = []
        self.kline_callbacks: List[Callable] = []
        
        # 数据缓存
        self.account_snapshot: Optional[ExtendedAccountSnapshot] = None
        self.open_orders: Dict[int, ExtendedOrder] = {}
        self.last_depth: Optional[ExtendedDepth] = None
        self.last_ticker: Optional[ExtendedTicker] = None
        self.last_klines: List[ExtendedKline] = []
        self.markets: Dict[str, MarketModel] = {}
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 订单簿缓存
        self.orderbooks: Dict[str, OrderBook] = {}
        
        # 价格缓存，用于检测 WebSocket 是否在更新
        self.last_depth_prices: Dict[str, Dict[str, Any]] = {}  # {symbol: {'bid': price, 'ask': price, 'timestamp': time}}
        # 记录WebSocket OrderBook连续“无数据”的次数，用于在极端情况下触发重建 WebSocket 连接
        self.orderbook_empty_count: Dict[str, int] = {}
        
        # 持久的事件循环和线程，用于管理 OrderBook WebSocket 连接
        self._orderbook_loop: Optional[asyncio.AbstractEventLoop] = None
        self._orderbook_thread: Optional[threading.Thread] = None
        self._orderbook_loop_lock = threading.Lock()
        
        # 订单缓存相关
        self.orders_cache_timestamp: float = 0  # 缓存时间戳
        self.orders_cache_ttl: float = 5.0  # 缓存有效期（秒），5秒内使用缓存
        self.orders_ws_subscribed: bool = False  # 是否已订阅WebSocket订单更新
        
        # 初始化标志
        self._initialized = False
    
    async def initialize(self):
        """初始化交易客户端"""
        if not self._initialized or self.trading_client is None:
            self.trading_client = PerpetualTradingClient(self.config, self.stark_account)
        # 获取市场信息
        try:
            markets_response = await self.trading_client.markets_info.get_markets()
            if hasattr(markets_response, 'data') and markets_response.data:
                self.markets = {market.name: market for market in markets_response.data}
                self._initialized = True
            else:
                # 即使没有市场数据，也标记为已初始化（trading_client已创建）
                # 市场信息可以在后续调用中获取
                self._initialized = True
                if not self.markets:
                    self.markets = {}
        except Exception as e:
            # 如果获取市场信息失败，但trading_client已创建，仍然标记为已初始化
            # 这样后续调用可以重试获取市场信息
            if self.trading_client is not None:
                self._initialized = True
                if not self.markets:
                    self.markets = {}
            raise  # 重新抛出异常，让调用者知道初始化过程中有问题
        
        # 启动持久的事件循环用于 OrderBook WebSocket 连接
        self._start_orderbook_event_loop()
    
    def _start_orderbook_event_loop(self):
        """启动持久的事件循环用于 OrderBook WebSocket 连接"""
        with self._orderbook_loop_lock:
            if self._orderbook_thread is not None and self._orderbook_thread.is_alive():
                return  # 已经启动
            
            def run_orderbook_loop():
                """在后台线程中运行持久的事件循环"""
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                self._orderbook_loop = new_loop
                
                # 设置异常处理器，捕获未处理的 Task 异常（如 WebSocket 连接超时）
                def handle_exception(loop, context):
                    """处理事件循环中的未处理异常"""
                    exception = context.get('exception')
                    if exception:
                        # 如果是 TimeoutError（WebSocket 连接超时），只记录警告，不打印完整堆栈
                        if isinstance(exception, (TimeoutError, asyncio.TimeoutError)):
                            print(f"[Extended] WebSocket连接超时（已自动处理，不影响现有连接）")
                        else:
                            # 其他异常打印详细信息
                            print(f"[Extended] OrderBook事件循环异常: {exception}")
                    else:
                        # 没有异常对象，打印上下文信息
                        print(f"[Extended] OrderBook事件循环异常: {context.get('message', '未知错误')}")
                
                new_loop.set_exception_handler(handle_exception)
                
                try:
                    new_loop.run_forever()
                except Exception as e:
                    print(f"[Extended] OrderBook事件循环错误: {e}")
                finally:
                    new_loop.close()
                    self._orderbook_loop = None
            
            self._orderbook_thread = threading.Thread(target=run_orderbook_loop, daemon=True)
            self._orderbook_thread.start()
            # 等待事件循环启动
            import time
            time.sleep(0.5)
            print(f"[Extended] 已启动OrderBook WebSocket事件循环线程")
    
    def _ensure_initialized(self):
        """确保客户端已初始化"""
        if not self._initialized:
            raise RuntimeError("客户端未初始化，请先调用 initialize() 方法")
    
    def _convert_order_side(self, side: str) -> OrderSide:
        """转换订单方向"""
        if side.upper() == "BUY":
            return OrderSide.BUY
        elif side.upper() == "SELL":
            return OrderSide.SELL
        else:
            raise ValueError(f"不支持的订单方向: {side}")
    
    def _convert_order_type(self, order_type: str) -> OrderType:
        """转换订单类型"""
        if order_type.upper() == "LIMIT":
            return OrderType.LIMIT
        elif order_type.upper() == "MARKET":
            return OrderType.MARKET
        elif order_type.upper() == "CONDITIONAL":
            return OrderType.CONDITIONAL
        else:
            raise ValueError(f"不支持的订单类型: {order_type}")
    
    def _convert_time_in_force(self, tif: str) -> TimeInForce:
        """转换订单有效期"""
        if tif.upper() == "GTC":
            return TimeInForce.GTT
        elif tif.upper() == "IOC":
            return TimeInForce.IOC
        elif tif.upper() == "FOK":
            return TimeInForce.FOK
        else:
            return TimeInForce.GTT  # 默认值
    
    def _convert_position_side(self, side: str) -> PositionSide:
        """转换持仓方向"""
        if side.upper() == "LONG":
            return PositionSide.LONG
        elif side.upper() == "SHORT":
            return PositionSide.SHORT
        else:
            raise ValueError(f"不支持的持仓方向: {side}")
    
    def _format_order(self, order_data: Any) -> ExtendedOrder:
        """格式化订单数据"""
        # 安全地获取枚举值
        def get_enum_value(obj, default=None):
            """安全地获取枚举值"""
            if obj is None:
                return default
            if hasattr(obj, 'value'):
                return obj.value
            return str(obj) if obj else default
        
        return ExtendedOrder(
            order_id=order_data.id,
            client_order_id=order_data.external_id,
            symbol=order_data.market,
            side=get_enum_value(order_data.side, 'UNKNOWN'),
            type=get_enum_value(order_data.type, 'UNKNOWN'),
            quantity=str(order_data.qty),
            price=str(order_data.price),
            status=get_enum_value(order_data.status, 'UNKNOWN'),
            time_in_force=get_enum_value(order_data.time_in_force if hasattr(order_data, 'time_in_force') else None, 'GTC'),
            executed_qty=str(order_data.filled_qty or 0),
            avg_price=str(order_data.average_price or 0),
            time=order_data.created_time,
            update_time=order_data.updated_time,
            reduce_only=getattr(order_data, 'reduce_only', False),
            # post_only字段在ExtendedOrder中不存在，移除
        )
    
    def _format_position(self, position: PositionModel) -> ExtendedAccountPosition:
        """格式化持仓数据（兼容不同字段名/类型）"""
        # 市场标识兼容
        symbol = getattr(position, 'market', None) or getattr(position, 'market_name', None) or getattr(position, 'symbol', '')
        # 持仓数量兼容
        size = getattr(position, 'size', None)
        if size is None:
            size = getattr(position, 'position_size', None)
        if size is None:
            size = getattr(position, 'quantity', None)
        # 可能是Decimal/str
        try:
            size_str = str(size)
        except Exception:
            size_str = "0"
        # 入场价兼容
        entry = getattr(position, 'open_price', None)
        if entry is None:
            entry = getattr(position, 'entry_price', None)
        if entry is None:
            entry = getattr(position, 'average_entry_price', None)
        # 未实现盈亏兼容
        upnl = getattr(position, 'unrealised_pnl', None)
        if upnl is None:
            upnl = getattr(position, 'unrealized_pnl', 0)
        # 杠杆
        lev = getattr(position, 'leverage', 0)
        # 方向：优先side字段，缺失时用size正负判断
        raw_side = getattr(position, 'side', None)
        if hasattr(raw_side, 'value'):
            position_side = raw_side.value
        elif isinstance(raw_side, str) and raw_side:
            position_side = raw_side
        else:
            try:
                f = float(size_str)
                position_side = 'LONG' if f > 0 else ('SHORT' if f < 0 else 'BOTH')
            except Exception:
                position_side = 'BOTH'
        # 更新时间
        updated = getattr(position, 'updated_at', None)
        if updated is None:
            updated = getattr(position, 'updated_time', 0)

        return ExtendedAccountPosition(
            symbol=symbol,
            position_amt=size_str,
            entry_price=str(entry if entry is not None else 0),
            unrealized_profit=str(upnl if upnl is not None else 0),
            leverage=str(lev if lev is not None else 0),
            position_side=position_side,
            update_time=updated or 0
        )
    
    def _format_balance(self, balance: BalanceModel) -> ExtendedAccountAsset:
        """格式化余额数据"""
        return ExtendedAccountAsset(
            asset=balance.collateral_name,
            wallet_balance=str(balance.balance),
            unrealized_profit=str(balance.unrealised_pnl),
            margin_balance=str(balance.equity),
            maint_margin="0",  # Extended API可能不提供此字段
            initial_margin=str(balance.initial_margin),
            position_initial_margin="0",  # Extended API可能不提供此字段
            open_order_initial_margin="0",  # Extended API可能不提供此字段
            cross_wallet_balance="0",  # Extended API可能不提供此字段
            cross_un_pnl="0",  # Extended API可能不提供此字段
            available_balance=str(balance.available_for_trade),
            max_withdraw_amount=str(balance.available_for_withdrawal),
            update_time=balance.updated_time
        )
    
    async def get_markets(self) -> Dict[str, MarketModel]:
        """获取所有市场信息"""
        self._ensure_initialized()
        if not self.markets:
            markets_response = await self.trading_client.markets_info.get_markets()
            if hasattr(markets_response, 'data') and markets_response.data:
                self.markets = {market.name: market for market in markets_response.data}
        return self.markets
    
    async def get_market(self, symbol: str) -> Optional[MarketModel]:
        """获取指定市场信息"""
        markets = await self.get_markets()
        return markets.get(symbol)
    
    async def get_ticker(self, symbol: str) -> ExtendedTicker:
        """获取Ticker数据"""
        self._ensure_initialized()
        market = await self.get_market(symbol)
        if not market:
            raise ValueError(f"未找到市场: {symbol}")
        
        stats = market.market_stats
        return ExtendedTicker(
            symbol=symbol,
            last_price=str(stats.last_price),
            open_price=str(stats.last_price - stats.daily_price_change),
            high_price=str(stats.daily_high),
            low_price=str(stats.daily_low),
            volume=str(stats.daily_volume),
            quote_volume=str(stats.daily_volume_base),
            price_change=str(stats.daily_price_change),
            price_change_percent=str(stats.daily_price_change / (stats.last_price - stats.daily_price_change) * 100 if stats.last_price != stats.daily_price_change else "0"),
            event_time=int(time.time() * 1000)
        )
    
    async def get_depth(self, symbol: str, limit: int = 20) -> ExtendedDepth:
        """获取深度数据（优先使用WebSocket，避免API限速）"""
        self._ensure_initialized()
        
        bids = []
        asks = []
        use_rest_api = False  # 默认不使用REST API
        
        try:
            print(f"[Extended] 尝试获取 {symbol} 的深度数据（优先使用WebSocket）...")
            
            # 优先使用WebSocket OrderBook获取实时数据
            try:
                # 创建或获取订单簿（在持久的事件循环中）
                if symbol not in self.orderbooks:
                    market = await self.get_market(symbol)
                    if not market:
                        print(f"[Extended] 未找到市场: {symbol}")
                        raise ValueError(f"未找到市场: {symbol}")
                    
                    print(f"[Extended] 创建WebSocket OrderBook连接...")
                    # 在持久的事件循环中创建 OrderBook
                    if self._orderbook_loop is not None and self._orderbook_loop.is_running():
                        # 使用持久的事件循环创建 OrderBook
                        # 注意：OrderBook 需要在持久的事件循环中创建和运行，这样 WebSocket 才能持续更新
                        future = asyncio.run_coroutine_threadsafe(
                            OrderBook.create(
                                self.config,
                                market_name=symbol,
                                start=True
                            ),
                            self._orderbook_loop
                        )
                        try:
                            self.orderbooks[symbol] = future.result(timeout=10)
                            print(f"[Extended] OrderBook已在持久事件循环中创建并启动")
                        except Exception as e:
                            print(f"[Extended] 在持久事件循环中创建OrderBook失败: {e}，尝试在当前事件循环中创建")
                            # 如果失败，回退到当前事件循环
                            self.orderbooks[symbol] = await OrderBook.create(
                                self.config,
                                market_name=symbol,
                                start=True
                            )
                    else:
                        # 如果没有持久的事件循环，在当前事件循环中创建
                        print(f"[Extended] 持久事件循环未运行，在当前事件循环中创建OrderBook")
                        self.orderbooks[symbol] = await OrderBook.create(
                            self.config,
                            market_name=symbol,
                            start=True
                        )
                
                orderbook = self.orderbooks[symbol]
                
                # 等待数据更新（如果订单簿刚创建）
                if not orderbook.best_bid() or not orderbook.best_ask():
                    print(f"[Extended] 等待WebSocket数据更新...")
                    await asyncio.sleep(2)  # 等待WebSocket连接建立和数据更新
                
                # 从WebSocket OrderBook获取多档数据
                # 注意：OrderBook可能只提供最佳买卖价，需要获取更多档位
                best_bid = orderbook.best_bid()
                best_ask = orderbook.best_ask()
                
                if best_bid and best_ask:
                    current_bid_price = float(best_bid.price)
                    current_ask_price = float(best_ask.price)
                    
                    # 检查价格是否在更新（只在价格变化时刷新时间戳）
                    current_time = time.time()
                    if symbol in self.last_depth_prices:
                        last_prices = self.last_depth_prices[symbol]
                        last_bid = last_prices.get('bid')
                        last_ask = last_prices.get('ask')
                        last_timestamp = last_prices.get('timestamp', 0)
                        
                        if last_bid == current_bid_price and last_ask == current_ask_price:
                            # 价格完全相同，检查是否长时间没有变化
                            if current_time - last_timestamp > 30.0:
                                # 认为 WebSocket 可能已经卡住，优先安全地关闭并移除旧的 OrderBook，
                                # 然后本次改用 REST 校验最新价格，下一次调用会重新创建 WebSocket 连接
                                print(f"[Extended] WebSocket OrderBook价格在30秒内未变化，认为可能已卡住，切换为REST并重建OrderBook...")
                                try:
                                    if symbol in self.orderbooks:
                                        ob = self.orderbooks.pop(symbol)
                                        # 尝试关闭旧的 OrderBook（如果 SDK 提供 close/stop 方法）
                                        close_fn = getattr(ob, "close", None) or getattr(ob, "stop", None)
                                        if callable(close_fn):
                                            close_fn()
                                except Exception as close_err:
                                    print(f"[Extended] 关闭旧OrderBook时出错: {close_err}")
                                use_rest_api = True
                        else:
                            # 价格发生了变化，刷新时间戳
                            self.last_depth_prices[symbol] = {
                                'bid': current_bid_price,
                                'ask': current_ask_price,
                                'timestamp': current_time
                            }
                    else:
                        # 第一次获取，记录价格
                        self.last_depth_prices[symbol] = {
                            'bid': current_bid_price,
                            'ask': current_ask_price,
                            'timestamp': current_time
                        }
                    
                    if not use_rest_api:
                        print(f"[Extended] WebSocket OrderBook - 最佳买价: {best_bid.price}, 最佳卖价: {best_ask.price}")
                        
                        # 添加最佳买卖价
                        bids.append(ExtendedDepthLevel(
                            price=str(best_bid.price),
                            quantity=str(best_bid.amount)
                        ))
                        asks.append(ExtendedDepthLevel(
                            price=str(best_ask.price),
                            quantity=str(best_ask.amount)
                        ))
                        
                        # 尝试获取更多档位（如果OrderBook支持）
                        # 注意：Extended的OrderBook可能只提供最佳价，如果需要更多档位，可能需要使用REST API
                        # 这里先获取最佳价，如果需要更多档位，可以fallback到REST API
                        if limit > 1:
                            print(f"[Extended] WebSocket OrderBook仅提供最佳价，如需更多档位将使用REST API")
                            # 如果需要更多档位，继续使用REST API获取
                            use_rest_api = True
                        else:
                            use_rest_api = False
                        
                        if bids and asks:
                            print(f"[Extended] WebSocket OrderBook成功获取深度数据: {len(bids)}档买盘, {len(asks)}档卖盘")
                            # 如果只需要最佳价，直接返回
                            if limit == 1:
                                return ExtendedDepth(
                                    symbol=symbol,
                                    last_update_id=int(time.time() * 1000),
                                    bids=bids,
                                    asks=asks,
                                    event_time=int(time.time() * 1000)
                                )
                    # WebSocket本次返回了有效数据，清空“无数据”计数
                    self.orderbook_empty_count[symbol] = 0
                else:
                    # 连续无数据计数+1
                    empty_count = self.orderbook_empty_count.get(symbol, 0) + 1
                    self.orderbook_empty_count[symbol] = empty_count
                    print(f"[Extended] WebSocket OrderBook暂无数据（连续 {empty_count} 次），尝试使用REST API...")
                    # 如果连续多次（比如 20 次）都没有任何数据，认为 WebSocket 连接可能异常，重建 OrderBook
                    if empty_count >= 20:
                        print(f"[Extended] {symbol} 的WebSocket OrderBook在长时间内均无数据，尝试重建OrderBook连接...")
                        try:
                            if symbol in self.orderbooks:
                                ob = self.orderbooks.pop(symbol)
                                close_fn = getattr(ob, "close", None) or getattr(ob, "stop", None)
                                if callable(close_fn):
                                    close_fn()
                        except Exception as close_err:
                            print(f"[Extended] 重建OrderBook前关闭旧连接时出错: {close_err}")
                        # 重置计数，下次调用会重新创建 OrderBook
                        self.orderbook_empty_count[symbol] = 0
                    use_rest_api = True
                    
            except Exception as e:
                print(f"[Extended] WebSocket OrderBook失败: {e}，尝试使用REST API...")
                use_rest_api = True
            
            # 如果需要更多档位或WebSocket失败，使用REST API作为fallback
            if use_rest_api:
                print(f"[Extended] 使用REST API获取最新深度数据...")
                try:
                    orderbook_snapshot = await self.trading_client.markets_info.get_orderbook_snapshot(market_name=symbol)
                    
                    if hasattr(orderbook_snapshot, 'error') and orderbook_snapshot.error:
                        print(f"[Extended] REST API错误: {orderbook_snapshot.error}")
                    elif hasattr(orderbook_snapshot, 'data') and orderbook_snapshot.data:
                        data = orderbook_snapshot.data
                        
                        # 如果WebSocket已经获取了最佳价，保留它；否则从REST API获取全部
                        if not bids or not asks:
                            # WebSocket失败，使用REST API获取全部数据
                            bids = []
                            asks = []
                        
                        # 解析买盘数据
                        if hasattr(data, 'bid') and data.bid:
                            # 如果已有WebSocket数据，只添加更多档位；否则替换
                            if not bids:
                                bids = []
                            for i, bid_level in enumerate(data.bid[:limit]):
                                if isinstance(bid_level, (list, tuple)) and len(bid_level) >= 2:
                                    price = str(bid_level[0])
                                    qty = str(bid_level[1])
                                elif hasattr(bid_level, 'price') and hasattr(bid_level, 'qty'):
                                    price = str(bid_level.price)
                                    qty = str(bid_level.qty)
                                else:
                                    continue
                                
                                # 避免重复添加最佳价（如果WebSocket已经提供了）
                                if bids and price == bids[0].price:
                                    continue
                                
                                bids.append(ExtendedDepthLevel(price=price, quantity=qty))
                            print(f"[Extended] REST API解析后买盘数量: {len(bids)}")
                        
                        # 解析卖盘数据
                        if hasattr(data, 'ask') and data.ask:
                            # 如果已有WebSocket数据，只添加更多档位；否则替换
                            if not asks:
                                asks = []
                            for i, ask_level in enumerate(data.ask[:limit]):
                                if isinstance(ask_level, (list, tuple)) and len(ask_level) >= 2:
                                    price = str(ask_level[0])
                                    qty = str(ask_level[1])
                                elif hasattr(ask_level, 'price') and hasattr(ask_level, 'qty'):
                                    price = str(ask_level.price)
                                    qty = str(ask_level.qty)
                                else:
                                    continue
                                
                                # 避免重复添加最佳价（如果WebSocket已经提供了）
                                if asks and price == asks[0].price:
                                    continue
                                
                                asks.append(ExtendedDepthLevel(price=price, quantity=qty))
                            print(f"[Extended] REST API解析后卖盘数量: {len(asks)}")
                except Exception as e:
                    print(f"[Extended] REST API获取失败: {e}")
            
            # 如果仍然没有数据，返回空深度数据
            if not bids and not asks:
                print(f"[Extended] 交易对 {symbol} 暂无深度数据")
            
            return ExtendedDepth(
                symbol=symbol,
                last_update_id=int(time.time() * 1000),
                bids=bids,
                asks=asks,
                event_time=int(time.time() * 1000)
            )
            
        except Exception as e:
            print(f"[Extended] 获取深度数据失败: {e}")
            import traceback
            traceback.print_exc()
            # 返回空的深度数据
            return ExtendedDepth(
                symbol=symbol,
                last_update_id=int(time.time() * 1000),
                bids=[],
                asks=[],
                event_time=int(time.time() * 1000)
            )
    
    async def get_account(self, force_refresh: bool = False) -> ExtendedAccountSnapshot:
        """获取账户信息"""
        self._ensure_initialized()
        
        # 检查缓存
        if not force_refresh and self.account_snapshot:
            return self.account_snapshot
        
        # 获取余额
        balance_response = await self.trading_client.account.get_balance()
        if hasattr(balance_response, 'error') and balance_response.error:
            raise Exception(f"获取余额失败: {balance_response.error}")
        
        balance = balance_response.data
        assets = [self._format_balance(balance)]
        
        # 获取持仓
        positions_response = await self.trading_client.account.get_positions()
        if hasattr(positions_response, 'error') and positions_response.error:
            raise Exception(f"获取持仓失败: {positions_response.error}")
        
        positions = [self._format_position(pos) for pos in positions_response.data]

        # 兜底校验：若余额初始保证金为0，且持仓尺寸极小/不存在，判定为无持仓（解决SDK延迟）
        try:
            has_margin = float(getattr(balance, 'initial_margin', 0) or 0) > 0
        except Exception:
            has_margin = True

        def _abs_float(v: str) -> float:
            try:
                return abs(float(v))
            except Exception:
                return 0.0

        total_size = sum(_abs_float(p.position_amt) for p in positions) if positions else 0.0
        # 使用市场最小下单量的一半作为阈值（若可取到）
        min_threshold = 0.0
        try:
            any_symbol = positions[0].symbol if positions else self.default_market
            m = await self.get_market(any_symbol)
            if m:
                from decimal import Decimal
                min_threshold = float(m.trading_config.min_order_size / Decimal('2'))
        except Exception:
            pass
        if not has_margin and total_size <= max(min_threshold, 1e-9):
            positions = []
        
        # 创建账户快照
        self.account_snapshot = ExtendedAccountSnapshot(
            fee_tier=0,  # Extended没有这个字段
            can_trade=True,
            can_deposit=True,
            can_withdraw=True,
            update_time=balance.updated_time,
            total_initial_margin=str(balance.initial_margin),
            total_maint_margin="0",  # Extended没有这个字段
            total_wallet_balance=str(balance.balance),
            total_unrealized_profit=str(balance.unrealised_pnl),
            total_margin_balance=str(balance.equity),
            total_position_initial_margin=str(balance.initial_margin),
            total_open_order_initial_margin="0",  # Extended没有这个字段
            total_cross_wallet_balance=str(balance.balance),
            total_cross_un_pnl=str(balance.unrealised_pnl),
            available_balance=str(balance.available_for_trade),
            max_withdraw_amount=str(balance.available_for_withdrawal),
            assets=assets,
            positions=positions
        )
        
        return self.account_snapshot
    
    async def get_open_orders(self, symbol: str = None, use_cache: bool = True) -> List[ExtendedOrder]:
        """
        获取未成交订单（优先使用缓存，避免API限速）
        
        Args:
            symbol: 交易对符号，None表示获取所有交易对的订单
            use_cache: 是否使用缓存，如果缓存有效且在TTL内，直接返回缓存数据
        
        Returns:
            未成交订单列表
        """
        self._ensure_initialized()
        
        # 检查缓存是否有效
        current_time = time.time()
        cache_valid = (
            use_cache and
            self.orders_cache_timestamp > 0 and
            (current_time - self.orders_cache_timestamp) < self.orders_cache_ttl
        )
        
        if cache_valid:
            cache_age = current_time - self.orders_cache_timestamp
            print(f"[Extended] 使用订单缓存（缓存时间: {cache_age:.2f}秒前，TTL: {self.orders_cache_ttl}秒）")
            # 从缓存中获取订单
            with self.lock:
                orders = list(self.open_orders.values())
            
            # 如果指定了symbol，过滤订单
            if symbol:
                orders = [order for order in orders if order.symbol == symbol and order.status in ['NEW', 'PARTIALLY_FILLED']]
            else:
                # 只返回未成交订单
                orders = [order for order in orders if order.status in ['NEW', 'PARTIALLY_FILLED']]
            
            return orders
        
        # 缓存无效或未启用，使用REST API获取
        print(f"[Extended] 使用REST API获取未成交订单（避免频繁调用，建议使用WebSocket订阅）...")
        orders_response = await self.trading_client.account.get_open_orders()
        if hasattr(orders_response, 'error') and orders_response.error:
            raise Exception(f"获取订单失败: {orders_response.error}")
        
        orders = []
        with self.lock:
            # 清空旧缓存
            self.open_orders.clear()
            # 更新缓存时间戳
            self.orders_cache_timestamp = time.time()
            
            for order_data in orders_response.data:
                if symbol and order_data.market != symbol:
                    continue
                
                order = self._format_order(order_data)
                orders.append(order)
                
                # 更新缓存（只缓存未成交订单）
                if order.status in ['NEW', 'PARTIALLY_FILLED']:
                    self.open_orders[order.order_id] = order
            
            # 更新缓存时间戳
            self.orders_cache_timestamp = current_time
        
        return orders
    
    async def create_order(self, symbol: str = None, side: str = None, order_type: str = None, 
                          quantity: float = None, price: float = None, params: Dict = None) -> ExtendedOrder:
        """创建订单"""
        self._ensure_initialized()
        
        # 支持两种调用方式：直接传参或传字典
        if params is not None and 'symbol' in params:
            # 从params字典中获取参数
            symbol = params['symbol']
            side = self._convert_order_side(params['side'])
            order_type = self._convert_order_type(params['type'])
            quantity = Decimal(params['quantity'])
            price = Decimal(params['price']) if 'price' in params else None
        else:
            # 直接传参方式
            if symbol is None or side is None or order_type is None or quantity is None:
                raise ValueError("缺少必需参数: symbol, side, order_type, quantity")
            side = self._convert_order_side(side)
            order_type = self._convert_order_type(order_type)
            quantity = Decimal(str(quantity))
            price = Decimal(str(price)) if price is not None else None
        
        # 获取市场信息
        market = await self.get_market(symbol)
        if not market:
            raise ValueError(f"未找到市场: {symbol}")
        
        # 调整数量精度 - 确保符合最小交易量要求
        min_order_size = market.trading_config.min_order_size
        if quantity < min_order_size:
            raise ValueError(f"订单数量 {quantity} 小于最小交易量 {min_order_size}")
        
        # 使用round_order_size方法调整数量精度
        quantity = market.trading_config.round_order_size(quantity)
        
        # 创建订单
        if order_type == OrderType.MARKET:
            # 市价单 - 使用IOC限价单模拟，并使用盘口价+容差，提升成交概率
            try:
                ob = await self.trading_client.markets_info.get_orderbook_snapshot(market_name=symbol)
                best_bid = None
                best_ask = None
                if hasattr(ob, 'data') and ob.data:
                    if hasattr(ob.data, 'bid') and ob.data.bid:
                        level = ob.data.bid[0]
                        best_bid = Decimal(str(level[0] if isinstance(level, (list, tuple)) else getattr(level, 'price', '0')))
                    if hasattr(ob.data, 'ask') and ob.data.ask:
                        level = ob.data.ask[0]
                        best_ask = Decimal(str(level[0] if isinstance(level, (list, tuple)) else getattr(level, 'price', '0')))
            except Exception:
                best_bid = None
                best_ask = None

            # 回退到最新价
            last_price = Decimal(str(market.market_stats.last_price))
            # 设定容差（0.3%），根据方向选择更易成交的价格
            tolerance = Decimal('0.003')
            if side == OrderSide.BUY:
                target = (best_ask if best_ask and best_ask > 0 else last_price) * (Decimal('1') + tolerance)
            else:
                target = (best_bid if best_bid and best_bid > 0 else last_price) * (Decimal('1') - tolerance)
            # 调整价格精度
            price_decimal = market.trading_config.round_price(target)

            # 市价单必须使用IOC时间类型
            reduce_only = params.get('reduceOnly', False) if params else False
            placed_order = await self.trading_client.place_order(
                market_name=symbol,
                amount_of_synthetic=quantity,
                price=price_decimal,
                side=side,
                time_in_force=TimeInForce.IOC,
                reduce_only=reduce_only
            )
        else:
            # 限价单 - 调整价格精度
            if price is not None:
                price = market.trading_config.round_price(price)
            
            reduce_only = params.get('reduceOnly', False) if params else False
            post_only = params.get('postOnly', False) if params else False
            # 默认使用GTT（Good Till Time），相当于GTC
            time_in_force = self._convert_time_in_force(params.get('timeInForce', 'GTC')) if params else TimeInForce.GTT
            
            placed_order = await self.trading_client.place_order(
                market_name=symbol,
                amount_of_synthetic=quantity,
                price=price,
                side=side,
                time_in_force=time_in_force,
                post_only=post_only,
                reduce_only=reduce_only
            )
        
        if hasattr(placed_order, 'error') and placed_order.error:
            raise Exception(f"下单失败: {placed_order.error}")
        
        # 创建订单对象
        order = ExtendedOrder(
            order_id=placed_order.data.id,
            client_order_id=placed_order.data.external_id,
            symbol=symbol,
            side=side.value,
            type=order_type.value,
            quantity=str(quantity),
            price=str(price) if price else "0",
            status="NEW",
            time_in_force=params.get('timeInForce', 'GTC') if params else 'GTC',
            reduce_only=reduce_only,
            time=int(time.time() * 1000),
            update_time=int(time.time() * 1000)
        )
        
        # 更新缓存
        with self.lock:
            self.open_orders[order.order_id] = order
            # 更新缓存时间戳
            self.orders_cache_timestamp = time.time()
        
        return order
    
    async def cancel_order(self, symbol: str, order_id: int = None, client_order_id: str = None) -> ExtendedOrder:
        """撤销订单"""
        self._ensure_initialized()
        
        if order_id:
            cancel_response = await self.trading_client.orders.cancel_order(order_id=order_id)
        elif client_order_id:
            # 通过client_order_id查找order_id
            orders = await self.get_open_orders(symbol)
            order_id = None
            for order in orders:
                if order.client_order_id == client_order_id:
                    order_id = order.order_id
                    break
            
            if not order_id:
                raise ValueError(f"未找到订单: {client_order_id}")
            
            cancel_response = await self.trading_client.orders.cancel_order(order_id=order_id)
        else:
            raise ValueError("必须提供order_id或client_order_id")
        
        if hasattr(cancel_response, 'error') and cancel_response.error:
            raise Exception(f"撤单失败: {cancel_response.error}")
        
        # 从缓存中移除
        with self.lock:
            self.open_orders.pop(order_id, None)
            # 更新缓存时间戳
            self.orders_cache_timestamp = time.time()
        
        # 返回被撤销的订单
        return ExtendedOrder(
            order_id=order_id,
            client_order_id=client_order_id or "",
            symbol=symbol,
            side="",
            type="",
            quantity="0",
            price="0",
            status="CANCELLED",
            time=int(time.time() * 1000),
            update_time=int(time.time() * 1000)
        )
    
    async def cancel_all_orders(self, symbol: str) -> List[Dict]:
        """撤销所有订单"""
        self._ensure_initialized()
        
        # 获取所有未成交订单
        orders = await self.get_open_orders(symbol)
        if not orders:
            return []
        
        # 批量撤销
        order_ids = [order.order_id for order in orders]
        cancel_response = await self.trading_client.orders.mass_cancel(order_ids=order_ids)
        
        if hasattr(cancel_response, 'error') and cancel_response.error:
            raise Exception(f"批量撤单失败: {cancel_response.error}")
        
        # 清空缓存
        with self.lock:
            self.open_orders.clear()
            # 更新缓存时间戳
            self.orders_cache_timestamp = time.time()
        
        return [{"orderId": order_id, "status": "CANCELLED"} for order_id in order_ids]
    
    async def cancel_order_by_price(self, symbol: str, price: float, side: str = None, 
                                   tolerance: float = 0.0) -> List[ExtendedOrder]:
        """
        撤销指定价格的未成交限价单
        
        Args:
            symbol: 交易对符号
            price: 要撤销的订单价格
            side: 订单方向，可选 "BUY" 或 "SELL"，为None时撤销所有方向的订单
            tolerance: 价格容差，允许价格在 [price - tolerance, price + tolerance] 范围内匹配
        
        Returns:
            被撤销的订单列表
        """
        self._ensure_initialized()
        
        # 获取所有未成交订单
        orders = await self.get_open_orders(symbol)
        if not orders:
            return []
        
        # 筛选匹配的订单
        matched_orders = []
        price_decimal = Decimal(str(price))
        tolerance_decimal = Decimal(str(tolerance))
        
        for order in orders:
            # 只处理限价单
            if order.type.upper() != "LIMIT":
                continue
            
            # 检查订单方向（如果指定了side）
            if side and order.side.upper() != side.upper():
                continue
            
            # 检查价格是否匹配（考虑容差）
            try:
                order_price = Decimal(order.price)
                price_diff = abs(order_price - price_decimal)
                
                if price_diff <= tolerance_decimal:
                    matched_orders.append(order)
            except (ValueError, TypeError) as e:
                print(f"[Extended] 解析订单价格失败: {order.price}, 错误: {e}")
                continue
        
        if not matched_orders:
            print(f"[Extended] 未找到匹配价格的订单: {symbol} @ {price}")
            return []
        
        # 批量撤销匹配的订单
        order_ids = [order.order_id for order in matched_orders]
        cancel_response = await self.trading_client.orders.mass_cancel(order_ids=order_ids)
        
        if hasattr(cancel_response, 'error') and cancel_response.error:
            raise Exception(f"批量撤单失败: {cancel_response.error}")
        
        # 从缓存中移除
        with self.lock:
            for order_id in order_ids:
                self.open_orders.pop(order_id, None)
            # 更新缓存时间戳
            self.orders_cache_timestamp = time.time()
        
        # 更新订单状态为已撤销
        cancelled_orders = []
        for order in matched_orders:
            cancelled_order = ExtendedOrder(
                order_id=order.order_id,
                client_order_id=order.client_order_id,
                symbol=order.symbol,
                side=order.side,
                type=order.type,
                quantity=order.quantity,
                price=order.price,
                status="CANCELLED",
                time_in_force=order.time_in_force,
                reduce_only=order.reduce_only,
                time=order.time,
                update_time=int(time.time() * 1000)
            )
            cancelled_orders.append(cancelled_order)
        
        print(f"[Extended] 成功撤销 {len(cancelled_orders)} 个匹配价格的订单: {symbol} @ {price}")
        return cancelled_orders
    
    async def create_order_by_usdt(self, symbol: str, side: str, usdt_amount: float, 
                                 order_type: str = "MARKET", price: float = None) -> ExtendedOrder:
        """按USDT金额下单"""
        self._ensure_initialized()
        
        # 获取市场信息
        market = await self.get_market(symbol)
        if not market:
            raise ValueError(f"未找到市场: {symbol}")
        
        # 获取当前价格
        if order_type == "MARKET" or price is None:
            ticker = await self.get_ticker(symbol)
            current_price = float(ticker.last_price)
        else:
            current_price = price
        
        # 计算数量
        quantity = Decimal(usdt_amount) / Decimal(current_price)
        
        # 根据市场配置调整数量精度
        quantity = market.trading_config.round_order_size(quantity)
        
        # 创建订单参数
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': str(quantity),
        }
        
        if order_type == "LIMIT" and price:
            # 调整价格精度
            price_decimal = market.trading_config.round_price(Decimal(price))
            params['price'] = str(price_decimal)
            params['timeInForce'] = 'GTC'
        
        return await self.create_order(params=params)
    
    async def close_position(self, symbol: str) -> ExtendedOrder:
        """平仓"""
        self._ensure_initialized()
        
        # 获取当前持仓
        positions = await self.get_positions(symbol)
        if not positions:
            raise ValueError(f"没有找到 {symbol} 的持仓")
        
        position = positions[0]
        position_amt = float(position.position_amt)
        if abs(position_amt) < 0.00001:
            raise ValueError(f"{symbol} 持仓量过小，无法平仓")
        
        # 确定平仓方向 - 使用position_side字段判断
        if position.position_side == "LONG":  # 多仓，需要卖出平仓
            side = 'SELL'
        else:  # 空仓，需要买入平仓
            side = 'BUY'
        
        # 获取市场信息以确保数量精度
        market = await self.get_market(symbol)
        if not market:
            raise ValueError(f"未找到市场: {symbol}")
        
        # 调整数量精度，确保不超过持仓数量
        actual_quantity = abs(position_amt)
        min_order_size = market.trading_config.min_order_size
        
        # 确保数量不小于最小交易量
        if actual_quantity < min_order_size:
            actual_quantity = min_order_size
        
        # 确保数量不超过持仓数量
        if actual_quantity > abs(position_amt):
            actual_quantity = abs(position_amt)
        
        # 使用IOC+盘口价±容差，确保尽快成交
        from x10.perpetual.orders import OrderSide, TimeInForce
        from decimal import Decimal

        # 使用round_order_size方法调整数量精度
        actual_quantity = market.trading_config.round_order_size(Decimal(str(actual_quantity)))

        close_side = OrderSide.BUY if side == 'BUY' else OrderSide.SELL

        # 获取盘口最优价
        best_bid = None
        best_ask = None
        try:
            ob = await self.trading_client.markets_info.get_orderbook_snapshot(market_name=symbol)
            if hasattr(ob, 'data') and ob.data:
                if hasattr(ob.data, 'bid') and ob.data.bid:
                    level = ob.data.bid[0]
                    best_bid = Decimal(str(level[0] if isinstance(level, (list, tuple)) else getattr(level, 'price', '0')))
                if hasattr(ob.data, 'ask') and ob.data.ask:
                    level = ob.data.ask[0]
                    best_ask = Decimal(str(level[0] if isinstance(level, (list, tuple)) else getattr(level, 'price', '0')))
        except Exception:
            pass

        last_price = Decimal(str(market.market_stats.last_price))
        tolerance = Decimal('0.003')  # 0.3%
        if close_side == OrderSide.BUY:
            target = (best_ask if best_ask and best_ask > 0 else last_price) * (Decimal('1') + tolerance)
        else:
            target = (best_bid if best_bid and best_bid > 0 else last_price) * (Decimal('1') - tolerance)
        price_decimal = market.trading_config.round_price(target)

        placed_order = await self.trading_client.place_order(
            market_name=symbol,
            amount_of_synthetic=actual_quantity,
            price=price_decimal,
            side=close_side,
            time_in_force=TimeInForce.IOC,
            reduce_only=True
        )
        
        if hasattr(placed_order, 'error') and placed_order.error:
            raise Exception(f"平仓订单创建失败: {placed_order.error}")
        
        # 创建订单对象
        order = ExtendedOrder(
            order_id=placed_order.data.id,
            client_order_id=placed_order.data.external_id,
            symbol=symbol,
            side=close_side.value,
            type="LIMIT",  # GTT限价单
            quantity=str(actual_quantity),
            price=str(price_decimal),
            status="NEW",
            time_in_force="GTT",
            reduce_only=True,
            time=int(time.time() * 1000),
            update_time=int(time.time() * 1000)
        )
        
        # 缓存订单
        with self.lock:
            self.open_orders[order.order_id] = order
        
        return order
    
    async def get_positions(self, symbol: str = None) -> List[ExtendedAccountPosition]:
        """获取持仓信息（带重试与零仓过滤）"""
        self._ensure_initialized()

        for attempt in range(3):
            try:
                positions_response = await self.trading_client.account.get_positions()
                if hasattr(positions_response, 'error') and positions_response.error:
                    raise Exception(f"获取持仓失败: {positions_response.error}")

                positions_all = [self._format_position(pos) for pos in positions_response.data]
                # 过滤零仓
                positions = []
                for p in positions_all:
                    try:
                        if abs(float(p.position_amt)) > 0:
                            positions.append(p)
                    except Exception:
                        pass

                if symbol:
                    positions = [pos for pos in positions if str(pos.symbol).upper() == str(symbol).upper()]

                if positions:
                    return positions

                # 若无持仓，稍等重试，避免撮合延迟
                await asyncio.sleep(0.4)
            except Exception as e:
                print(f"[Extended] 获取持仓失败(第{attempt+1}次): {e}")
                await asyncio.sleep(0.3)

        return []
    
    async def close_position_by_quantity(self, symbol: str, quantity: float) -> ExtendedOrder:
        """按指定数量平仓"""
        self._ensure_initialized()
        
        # 获取当前持仓
        positions = await self.get_positions(symbol)
        if not positions:
            raise Exception(f"未找到持仓: {symbol}")
        
        target_position = positions[0]  # 取第一个持仓
        position_amt = abs(float(target_position.position_amt))
        
        # 确保平仓数量不超过持仓数量
        if quantity > position_amt:
            quantity = position_amt
            print(f"警告: 平仓数量调整为持仓数量: {quantity}")
        
        # 确定平仓方向
        if target_position.position_side == "LONG":
            close_side = "SELL"
        else:
            close_side = "BUY"
        
        # 获取市场信息以确保数量精度
        market = await self.get_market(symbol)
        if not market:
            raise ValueError(f"未找到市场: {symbol}")
        
        # 调整数量精度
        min_order_size = market.trading_config.min_order_size
        if quantity < min_order_size:
            quantity = min_order_size
        
        # 使用IOC+盘口价±容差，确保尽快成交
        from x10.perpetual.orders import OrderSide, TimeInForce
        from decimal import Decimal

        # 使用round_order_size方法调整数量精度
        quantity = market.trading_config.round_order_size(Decimal(str(quantity)))

        order_side = OrderSide.BUY if close_side == 'BUY' else OrderSide.SELL

        best_bid = None
        best_ask = None
        try:
            ob = await self.trading_client.markets_info.get_orderbook_snapshot(market_name=symbol)
            if hasattr(ob, 'data') and ob.data:
                if hasattr(ob.data, 'bid') and ob.data.bid:
                    level = ob.data.bid[0]
                    best_bid = Decimal(str(level[0] if isinstance(level, (list, tuple)) else getattr(level, 'price', '0')))
                if hasattr(ob.data, 'ask') and ob.data.ask:
                    level = ob.data.ask[0]
                    best_ask = Decimal(str(level[0] if isinstance(level, (list, tuple)) else getattr(level, 'price', '0')))
        except Exception:
            pass

        last_price = Decimal(str(market.market_stats.last_price))
        tolerance = Decimal('0.003')
        if order_side == OrderSide.BUY:
            target = (best_ask if best_ask and best_ask > 0 else last_price) * (Decimal('1') + tolerance)
        else:
            target = (best_bid if best_bid and best_bid > 0 else last_price) * (Decimal('1') - tolerance)
        price_decimal = market.trading_config.round_price(target)

        placed_order = await self.trading_client.place_order(
            market_name=symbol,
            amount_of_synthetic=quantity,
            price=price_decimal,
            side=order_side,
            time_in_force=TimeInForce.IOC,
            reduce_only=True
        )
        
        if hasattr(placed_order, 'error') and placed_order.error:
            raise Exception(f"平仓订单创建失败: {placed_order.error}")
        
        # 创建订单对象
        order = ExtendedOrder(
            order_id=placed_order.data.id,
            client_order_id=placed_order.data.external_id,
            symbol=symbol,
            side=order_side.value,
            type="LIMIT",  # GTT限价单
            quantity=str(quantity),
            price=str(price_decimal),
            status="NEW",
            time_in_force="GTT",
            reduce_only=True,
            time=int(time.time() * 1000),
            update_time=int(time.time() * 1000)
        )
        
        # 缓存订单
        with self.lock:
            self.open_orders[order.order_id] = order
        
        return order
    
    async def get_leverage(self, symbol: str) -> int:
        """获取杠杆倍数"""
        self._ensure_initialized()
        
        leverage_response = await self.trading_client.account.get_leverage(market_names=[symbol])
        if hasattr(leverage_response, 'error') and leverage_response.error:
            raise Exception(f"获取杠杆失败: {leverage_response.error}")
        
        for leverage_data in leverage_response.data:
            if leverage_data.market == symbol:
                return int(leverage_data.leverage)
        
        return 1  # 默认杠杆
    
    async def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """设置杠杆倍数"""
        self._ensure_initialized()
        
        leverage_decimal = Decimal(leverage)
        update_response = await self.trading_client.account.update_leverage(
            market_name=symbol, 
            leverage=leverage_decimal
        )
        
        if hasattr(update_response, 'error') and update_response.error:
            raise Exception(f"设置杠杆失败: {update_response.error}")
        
        return {"symbol": symbol, "leverage": leverage}
    
    def watch_order_book(self, symbol: str, callback=None):
        """监听订单簿变化"""
        if not callback:
            return False
        
        # 初始化深度回调
        if symbol not in self.depth_callbacks:
            self.depth_callbacks[symbol] = []
        self.depth_callbacks[symbol].append(callback)
        
        # 启动订单簿监听（在后台线程中运行）
        def start_orderbook_thread():
            async def start_orderbook():
                try:
                    market = await self.get_market(symbol)
                    if not market:
                        print(f"[Extended] 未找到市场: {symbol}")
                        return
                    
                    orderbook = await OrderBook.create(
                        self.config,
                        market_name=symbol,
                        start=True,
                        best_ask_change_callback=self._on_best_ask_change,
                        best_bid_change_callback=self._on_best_bid_change
                    )
                    
                    self.orderbooks[symbol] = orderbook
                    print(f"[Extended] 开始监听 {symbol} 订单簿")
                    
                except Exception as e:
                    print(f"[Extended] 启动订单簿监听失败: {e}")
            
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(start_orderbook())
                # 保持事件循环运行
                loop.run_forever()
            except Exception as e:
                print(f"[Extended] 订单簿监听异常: {e}")
            finally:
                loop.close()
        
        # 在后台线程中启动
        thread = threading.Thread(target=start_orderbook_thread, daemon=True)
        thread.start()
        
        return True
    
    def _on_best_ask_change(self, best_ask):
        """最佳卖价变化回调"""
        if best_ask:
            # 触发深度更新回调
            for symbol, callbacks in self.depth_callbacks.items():
                if symbol in self.orderbooks:
                    orderbook = self.orderbooks[symbol]
                    best_bid = orderbook.best_bid()
                    
                    depth = ExtendedDepth(
                        symbol=symbol,
                        last_update_id=int(time.time() * 1000),
                        bids=[ExtendedDepthLevel(price=str(best_bid.price), quantity=str(best_bid.quantity))] if best_bid else [],
                        asks=[ExtendedDepthLevel(price=str(best_ask.price), quantity=str(best_ask.quantity))],
                        event_time=int(time.time() * 1000)
                    )
                    
                    for callback in callbacks:
                        try:
                            callback(depth)
                        except Exception as e:
                            print(f"[Extended] 深度更新回调错误: {e}")
    
    def _on_best_bid_change(self, best_bid):
        """最佳买价变化回调"""
        if best_bid:
            # 触发深度更新回调
            for symbol, callbacks in self.depth_callbacks.items():
                if symbol in self.orderbooks:
                    orderbook = self.orderbooks[symbol]
                    best_ask = orderbook.best_ask()
                    
                    depth = ExtendedDepth(
                        symbol=symbol,
                        last_update_id=int(time.time() * 1000),
                        bids=[ExtendedDepthLevel(price=str(best_bid.price), quantity=str(best_bid.quantity))],
                        asks=[ExtendedDepthLevel(price=str(best_ask.price), quantity=str(best_ask.quantity))] if best_ask else [],
                        event_time=int(time.time() * 1000)
                    )
                    
                    for callback in callbacks:
                        try:
                            callback(depth)
                        except Exception as e:
                            print(f"[Extended] 深度更新回调错误: {e}")
    
    def watch_account(self, callback: Callable[[ExtendedAccountSnapshot], None]):
        """监听账户更新"""
        self.account_callbacks.append(callback)
    
    def watch_order(self, callback: Callable[[List[ExtendedOrder]], None]):
        """监听订单更新"""
        self.order_callbacks.append(callback)
    
    def watch_depth(self, symbol: str, callback: Callable[[ExtendedDepth], None]):
        """监听深度更新"""
        self.watch_order_book(symbol, callback)
    
    def watch_ticker(self, symbol: str, callback: Callable[[ExtendedTicker], None]):
        """监听Ticker更新"""
        self.ticker_callbacks.append(callback)
        
        # 启动定时器轮询Ticker
        def poll_ticker():
            while True:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    ticker = loop.run_until_complete(self.get_ticker(symbol))
                    loop.close()
                    
                    for callback in self.ticker_callbacks:
                        try:
                            callback(ticker)
                        except Exception as e:
                            print(f"[Extended] Ticker更新回调错误: {e}")
                    
                    time.sleep(1)  # 每秒更新一次
                except Exception as e:
                    print(f"[Extended] 轮询Ticker失败: {e}")
                    time.sleep(1)
        
        thread = threading.Thread(target=poll_ticker, daemon=True)
        thread.start()
    
    def watch_kline(self, symbol: str, interval: str, callback: Callable[[List[ExtendedKline]], None]):
        """监听K线更新"""
        self.kline_callbacks.append(callback)
        
        # 启动定时器轮询K线
        def poll_klines():
            while True:
                try:
                    # Extended暂不支持K线数据，使用Ticker数据模拟
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    ticker = loop.run_until_complete(self.get_ticker(symbol))
                    loop.close()
                    
                    # 创建模拟K线数据
                    kline = ExtendedKline(
                        open_time=int(time.time() * 1000),
                        open=ticker.last_price,
                        high=ticker.high_price,
                        low=ticker.low_price,
                        close=ticker.last_price,
                        volume=ticker.volume,
                        close_time=int(time.time() * 1000),
                        quote_asset_volume=ticker.quote_volume,
                        number_of_trades=0,
                        taker_buy_base_asset_volume="0",
                        taker_buy_quote_asset_volume="0",
                        event_time=int(time.time() * 1000)
                    )
                    
                    for callback in self.kline_callbacks:
                        try:
                            callback([kline])
                        except Exception as e:
                            print(f"[Extended] K线更新回调错误: {e}")
                    
                    time.sleep(1)  # 每秒更新一次
                except Exception as e:
                    print(f"[Extended] 轮询K线失败: {e}")
                    time.sleep(1)
        
        thread = threading.Thread(target=poll_klines, daemon=True)
        thread.start()
    
    async def close(self):
        """关闭客户端"""
        if self.trading_client:
            await self.trading_client.close()
        
        # 关闭所有订单簿
        for orderbook in self.orderbooks.values():
            await orderbook.close()
        
        self.orderbooks.clear()
        self._initialized = False
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, '_initialized') and self._initialized:
            try:
                # 在析构函数中不能使用异步操作
                # 只清理同步资源
                self.orderbooks.clear()
                self._initialized = False
            except:
                pass
