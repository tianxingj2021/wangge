"""
API数据模型（Pydantic Schemas）
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from decimal import Decimal


class ExchangeConfig(BaseModel):
    """交易所配置"""
    name: str = Field(..., description="交易所名称")
    api_key: str = Field(..., description="API密钥")
    secret_key: str = Field(..., description="密钥")
    testnet: bool = Field(False, description="是否使用测试网")
    account_alias: Optional[str] = Field(None, description="账号别名（用于区分同一交易所的多个账号）")
    
    # Extended交易所特定配置
    public_key: Optional[str] = Field(None, description="Extended公钥")
    private_key: Optional[str] = Field(None, description="Extended私钥（如果与secret_key不同）")
    vault: Optional[int] = Field(None, description="Extended金库ID")
    default_market: Optional[str] = Field(None, description="Extended默认交易对")


class OrderRequest(BaseModel):
    """下单请求"""
    symbol: str = Field(..., description="交易对符号")
    side: str = Field(..., description="买卖方向: buy/sell")
    order_type: str = Field(..., description="订单类型: limit/market")
    quantity: str = Field(..., description="数量")
    price: Optional[str] = Field(None, description="价格（限价单必填）")


class OrderResponse(BaseModel):
    """订单响应"""
    order_id: str
    symbol: str
    side: str
    type: str
    quantity: str
    price: Optional[str] = None
    status: str
    message: Optional[str] = None


class BalanceResponse(BaseModel):
    """余额响应"""
    currency: Optional[str] = None
    available: str
    frozen: str
    total: str


class GridStrategyConfig(BaseModel):
    """网格策略配置"""
    symbol: str = Field(..., description="交易对符号")
    upper_price: str = Field(..., description="网格上边界价格")
    lower_price: str = Field(..., description="网格下边界价格")
    grid_count: int = Field(..., description="网格数量", ge=2)
    investment: str = Field(..., description="总投资金额", gt="0")
    order_type: str = Field("limit", description="订单类型")
    account_key: Optional[str] = Field(None, description="账号唯一标识（account_key）")
    exchange_name: Optional[str] = Field(None, description="交易所名称（向后兼容，已废弃，请使用account_key）")


class SlidingWindowGridStrategyConfig(BaseModel):
    """滑动窗口网格策略配置"""
    symbol: str = Field(..., description="交易对符号")
    order_size: str = Field(..., description="每单数量")
    account_key: Optional[str] = Field(None, description="账号唯一标识（account_key）")
    exchange_name: Optional[str] = Field(None, description="交易所名称（向后兼容，已废弃，请使用account_key）")
    total_orders: Optional[int] = Field(18, description="总订单数")
    window_percent: Optional[float] = Field(0.12, description="窗口宽度百分比（0.12表示12%）")
    sell_ratio: Optional[float] = Field(0.5, description="卖单比例（0.5表示50%）")
    buy_ratio: Optional[float] = Field(0.5, description="买单比例（0.5表示50%）")
    base_price_interval: Optional[float] = Field(10.0, description="基础价格间距")
    safe_gap: Optional[float] = Field(20.0, description="安全偏移")
    max_drift_buffer: Optional[float] = Field(2000.0, description="最大偏移缓冲")
    min_valid_price: Optional[float] = Field(10000.0, description="最低有效价格")
    max_multiplier: Optional[float] = Field(15.0, description="最大开仓倍数")
    order_cooldown: Optional[float] = Field(1.5, description="订单冷却时间（秒）")
    
    @field_validator('order_size')
    @classmethod
    def validate_order_size(cls, v: str) -> str:
        """验证每单数量必须大于0"""
        try:
            value = Decimal(str(v))
            if value <= 0:
                raise ValueError("每单数量必须大于0")
            return str(v)
        except (ValueError, TypeError):
            raise ValueError("每单数量必须是有效的数字")


class StrategyStatus(BaseModel):
    """策略状态"""
    is_running: bool
    symbol: str
    upper_price: str
    lower_price: str
    grid_count: int
    current_price: str
    active_orders: int
    filled_orders: int
    grid_levels: List[str]


class StrategyResponse(BaseModel):
    """策略响应"""
    strategy_id: str
    status: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

