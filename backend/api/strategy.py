"""
策略相关API
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Union, Optional
from decimal import Decimal
from backend.models.schemas import (
    GridStrategyConfig, 
    SlidingWindowGridStrategyConfig,
    StrategyResponse, 
    StrategyStatus
)
from exchanges.factory import ExchangeFactory
from core.order_manager import OrderManager
from core.account_manager import AccountManager
from core.position_manager import PositionManager
from strategies.grid import GridStrategy
from strategies.sliding_window_grid import SlidingWindowGridStrategy
from core.config_manager import get_config_manager
import uuid

router = APIRouter(prefix="/strategy", tags=["策略"])

# 策略实例存储（实际应用中应使用数据库或Redis）
_strategies: Dict[str, Union[GridStrategy, SlidingWindowGridStrategy]] = {}


def normalize_symbol(symbol: str, exchange_name: Optional[str] = None) -> str:
    """
    规范化交易对符号
    
    如果用户只输入基础代币（如 "BTC"），自动补全为完整交易对（如 "BTC-USD"）
    
    Args:
        symbol: 用户输入的交易对或基础代币
        exchange_name: 交易所名称，用于获取默认配置
        
    Returns:
        规范化后的交易对符号
    """
    symbol = symbol.strip().upper()
    
    # 如果已经包含分隔符（- 或 /），直接规范化
    if '-' in symbol or '/' in symbol:
        # 简单的规范化：替换 / 为 -，USDT 转换为 USD
        symbol = symbol.replace('/', '-')
        if symbol.endswith('-USDT'):
            symbol = symbol.replace('-USDT', '-USD')
        return symbol
    
    # 如果只输入了基础代币（如 "BTC"），补全为 "BTC-USD"
    # 尝试从交易所配置获取默认计价货币
    quote_currency = 'USD'  # 默认使用 USD
    
    if exchange_name:
        try:
            config_manager = get_config_manager()
            config = config_manager.get_exchange_config(exchange_name)
            if config:
                # 从 default_market 推断计价货币（如 "BTC-USD" -> "USD"）
                default_market = config.get('default_market', 'BTC-USD')
                if isinstance(default_market, str) and '-' in default_market:
                    quote_currency = default_market.split('-')[-1]
        except Exception:
            pass
    
    return f"{symbol}-{quote_currency}"


def get_managers(account_key: Optional[str] = None, exchange_name: Optional[str] = None):
    """
    获取管理器实例（使用实例池）
    
    Args:
        account_key: 账号唯一标识（优先使用）
        exchange_name: 交易所名称（向后兼容，如果account_key为None时使用）
    """
    from core.exchange_pool import ExchangeInstancePool
    from core.config_manager import get_config_manager
    
    # 优先使用account_key
    if account_key:
        try:
            return ExchangeInstancePool.get_managers(account_key)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    # 向后兼容：如果提供了exchange_name，尝试查找对应的account_key
    if exchange_name:
        config_manager = get_config_manager()
        config = config_manager.get_exchange_config(exchange_name)
        if config and config.get('account_key'):
            try:
                return ExchangeInstancePool.get_managers(config['account_key'])
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(
                status_code=404,
                detail=f"交易所 {exchange_name} 的配置不存在"
            )
    
    # 如果都没有提供，获取第一个配置的账号
    config_manager = get_config_manager()
    all_exchanges = config_manager.get_all_exchanges()
    if not all_exchanges:
        raise HTTPException(
            status_code=400,
            detail="交易所未配置，请先在前端配置交易所API密钥"
        )
    
    # 使用第一个账号的account_key
    first_account_key = next(iter(all_exchanges.keys()))
    try:
        return ExchangeInstancePool.get_managers(first_account_key)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grid/start", response_model=StrategyResponse)
async def start_grid_strategy(
    config: GridStrategyConfig
):
    """启动网格策略"""
    try:
        # 确定account_key
        account_key = config.account_key
        if not account_key and config.exchange_name:
            # 向后兼容：从exchange_name查找account_key
            from core.config_manager import get_config_manager
            config_manager = get_config_manager()
            exchange_config = config_manager.get_exchange_config(config.exchange_name)
            if exchange_config:
                account_key = exchange_config.get('account_key')
        
        if not account_key:
            raise HTTPException(status_code=400, detail="必须提供account_key或exchange_name")
        
        managers = get_managers(account_key=account_key)
        order_manager, account_manager, position_manager = managers
        
        # 获取交易所名称用于规范化交易对
        from core.config_manager import get_config_manager
        config_manager = get_config_manager()
        account_config = config_manager.get_account_config(account_key)
        exchange_name = account_config.get('name') if account_config else None
        
        # 规范化交易对符号（如果用户只输入基础代币，自动补全）
        normalized_symbol = normalize_symbol(config.symbol, exchange_name)
        
        # 创建策略实例
        strategy = GridStrategy(
            order_manager=order_manager,
            account_manager=account_manager,
            position_manager=position_manager,
            account_key=account_key,
            symbol=normalized_symbol,
            upper_price=config.upper_price,
            lower_price=config.lower_price,
            grid_count=config.grid_count,
            investment=config.investment,
            order_type=config.order_type
        )
        
        # 启动策略
        result = strategy.start()
        
        # 保存策略实例
        strategy_id = str(uuid.uuid4())
        _strategies[strategy_id] = strategy
        
        return StrategyResponse(
            strategy_id=strategy_id,
            status=result.get('status', 'unknown'),
            message=result.get('message'),
            data=result
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grid/{strategy_id}/stop", response_model=StrategyResponse)
async def stop_grid_strategy(strategy_id: str):
    """停止网格策略"""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    try:
        strategy = _strategies[strategy_id]
        result = strategy.stop()
        
        # 可选：从存储中移除
        # del _strategies[strategy_id]
        
        return StrategyResponse(
            strategy_id=strategy_id,
            status=result.get('status', 'stopped'),
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grid/{strategy_id}/start", response_model=StrategyResponse)
async def restart_grid_strategy(strategy_id: str):
    """重新启动网格策略"""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    try:
        strategy = _strategies[strategy_id]
        
        # 如果策略已经在运行，返回错误
        if strategy.is_running:
            raise HTTPException(status_code=400, detail="策略已在运行中")
        
        # 重新启动策略
        result = strategy.start()
        
        return StrategyResponse(
            strategy_id=strategy_id,
            status=result.get('status', 'started'),
            message=result.get('message'),
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grid/{strategy_id}/update", response_model=StrategyResponse)
async def update_grid_strategy(strategy_id: str):
    """更新网格策略"""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    try:
        strategy = _strategies[strategy_id]
        result = strategy.update()
        
        return StrategyResponse(
            strategy_id=strategy_id,
            status=result.get('status', 'updated'),
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grid/{strategy_id}/status", response_model=StrategyStatus)
async def get_grid_strategy_status(strategy_id: str):
    """获取网格策略状态"""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    try:
        strategy = _strategies[strategy_id]
        status = strategy.get_status()
        return StrategyStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_strategies():
    """获取所有策略列表"""
    from core.config_manager import get_config_manager
    config_manager = get_config_manager()
    
    strategies = []
    for sid, s in _strategies.items():
        strategy_info = {
            "strategy_id": sid,
            "symbol": s.symbol,
            "is_running": s.is_running,
            "strategy_type": "grid" if isinstance(s, GridStrategy) else "sliding_window_grid"
        }
        
        # 添加账号信息
        if hasattr(s, 'account_key') and s.account_key:
            account_config = config_manager.get_account_config(s.account_key)
            if account_config:
                strategy_info["account_key"] = s.account_key
                strategy_info["account_alias"] = account_config.get('account_alias', s.account_key)
                strategy_info["exchange_name"] = account_config.get('name', '')
        
        strategies.append(strategy_info)
    
    return {"strategies": strategies}


@router.get("/types")
async def get_strategy_types():
    """获取可用的策略类型列表"""
    return {
        "strategy_types": [
            {
                "type": "grid",
                "name": "传统网格策略",
                "description": "在固定价格区间内设置买卖网格",
                "config_fields": [
                    {"name": "symbol", "label": "交易对", "type": "text", "required": True},
                    {"name": "upper_price", "label": "上边界价格", "type": "number", "required": True},
                    {"name": "lower_price", "label": "下边界价格", "type": "number", "required": True},
                    {"name": "grid_count", "label": "网格数量", "type": "number", "required": True, "min": 2},
                    {"name": "investment", "label": "投资金额", "type": "number", "required": True},
                ]
            },
            {
                "type": "sliding_window_grid",
                "name": "滑动窗口网格策略",
                "description": "以当前价格为中心，动态调整买卖单的滑动窗口网格",
                "config_fields": [
                    {"name": "symbol", "label": "交易对", "type": "text", "required": True, "placeholder": "BTC-USD"},
                    {"name": "order_size", "label": "每单数量", "type": "number", "required": True, "step": "0.0001", "placeholder": "0.001"},
                    {"name": "total_orders", "label": "总订单数", "type": "number", "required": False, "default": 18, "min": 2},
                    {"name": "window_percent", "label": "窗口宽度百分比", "type": "number", "required": False, "default": 0.12, "step": "0.01", "placeholder": "0.12表示12%"},
                    {"name": "sell_ratio", "label": "卖单比例", "type": "number", "required": False, "default": 0.5, "step": "0.1", "placeholder": "0.5表示50%"},
                    {"name": "buy_ratio", "label": "买单比例", "type": "number", "required": False, "default": 0.5, "step": "0.1", "placeholder": "0.5表示50%"},
                    {"name": "base_price_interval", "label": "基础价格间距", "type": "number", "required": False, "default": 10.0, "step": "0.1"},
                    {"name": "safe_gap", "label": "安全偏移", "type": "number", "required": False, "default": 20.0, "step": "0.1"},
                    {"name": "max_drift_buffer", "label": "最大偏移缓冲", "type": "number", "required": False, "default": 2000.0, "step": "1"},
                    {"name": "min_valid_price", "label": "最低有效价格", "type": "number", "required": False, "default": 10000.0, "step": "1"},
                    {"name": "max_multiplier", "label": "最大开仓倍数", "type": "number", "required": False, "default": 15.0, "step": "0.1"},
                    {"name": "order_cooldown", "label": "订单冷却时间（秒）", "type": "number", "required": False, "default": 1.5, "step": "0.1"},
                ]
            }
        ]
    }


@router.post("/sliding-window-grid/start", response_model=StrategyResponse)
async def start_sliding_window_grid_strategy(
    config: SlidingWindowGridStrategyConfig
):
    """启动滑动窗口网格策略"""
    try:
        # 确定account_key
        account_key = config.account_key
        if not account_key and config.exchange_name:
            # 向后兼容：从exchange_name查找account_key
            from core.config_manager import get_config_manager
            config_manager = get_config_manager()
            exchange_config = config_manager.get_exchange_config(config.exchange_name)
            if exchange_config:
                account_key = exchange_config.get('account_key')
        
        if not account_key:
            raise HTTPException(status_code=400, detail="必须提供account_key或exchange_name")
        
        managers = get_managers(account_key=account_key)
        order_manager, account_manager, position_manager = managers
        
        # 获取交易所名称用于规范化交易对
        from core.config_manager import get_config_manager
        config_manager = get_config_manager()
        account_config = config_manager.get_account_config(account_key)
        exchange_name = account_config.get('name') if account_config else None
        
        # 规范化交易对符号（如果用户只输入基础代币，自动补全）
        normalized_symbol = normalize_symbol(config.symbol, exchange_name)
        
        # 创建策略实例
        strategy = SlidingWindowGridStrategy(
            order_manager=order_manager,
            account_manager=account_manager,
            position_manager=position_manager,
            account_key=account_key,
            symbol=normalized_symbol,
            order_size=Decimal(str(config.order_size)),
            total_orders=config.total_orders,
            window_percent=config.window_percent,
            sell_ratio=config.sell_ratio,
            buy_ratio=config.buy_ratio,
            base_price_interval=config.base_price_interval,
            safe_gap=config.safe_gap,
            max_drift_buffer=config.max_drift_buffer,
            min_valid_price=config.min_valid_price,
            max_multiplier=config.max_multiplier,
            order_cooldown=config.order_cooldown
        )
        
        # 先保存策略实例（在启动前保存，这样即使启动失败也能返回策略ID）
        strategy_id = str(uuid.uuid4())
        _strategies[strategy_id] = strategy
        
        # 启动策略
        result = strategy.start()
        
        # 如果启动失败，仍然返回策略ID，但状态标记为错误
        # 这样前端可以显示错误信息，用户可以选择重试或删除策略
        
        return StrategyResponse(
            strategy_id=strategy_id,
            status=result.get('status', 'unknown'),
            message=result.get('message'),
            data=result
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sliding-window-grid/{strategy_id}/stop", response_model=StrategyResponse)
async def stop_sliding_window_grid_strategy(strategy_id: str):
    """停止滑动窗口网格策略"""
    if strategy_id not in _strategies:
        # 策略不存在可能是因为服务器重启导致内存清空
        # 返回一个友好的错误信息，建议用户重新启动策略
        raise HTTPException(
            status_code=404, 
            detail=f"策略不存在（ID: {strategy_id}）。可能原因：服务器重启导致策略状态丢失。请重新启动策略。"
        )
    
    strategy = _strategies[strategy_id]
    if not isinstance(strategy, SlidingWindowGridStrategy):
        raise HTTPException(status_code=400, detail="策略类型不匹配")
    
    try:
        result = strategy.stop()
        # 停止后不删除策略，保留在内存中以便查询状态
        return StrategyResponse(
            strategy_id=strategy_id,
            status=result.get('status', 'stopped'),
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sliding-window-grid/{strategy_id}/start", response_model=StrategyResponse)
async def restart_sliding_window_grid_strategy(strategy_id: str):
    """重新启动滑动窗口网格策略"""
    if strategy_id not in _strategies:
        raise HTTPException(
            status_code=404, 
            detail=f"策略不存在（ID: {strategy_id}）"
        )
    
    strategy = _strategies[strategy_id]
    if not isinstance(strategy, SlidingWindowGridStrategy):
        raise HTTPException(status_code=400, detail="策略类型不匹配")
    
    try:
        # 如果策略已经在运行，返回错误
        if strategy.is_running:
            raise HTTPException(status_code=400, detail="策略已在运行中")
        
        # 重新启动策略
        result = strategy.start()
        
        return StrategyResponse(
            strategy_id=strategy_id,
            status=result.get('status', 'started'),
            message=result.get('message'),
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sliding-window-grid/{strategy_id}/update", response_model=StrategyResponse)
async def update_sliding_window_grid_strategy(strategy_id: str):
    """更新滑动窗口网格策略"""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    strategy = _strategies[strategy_id]
    if not isinstance(strategy, SlidingWindowGridStrategy):
        raise HTTPException(status_code=400, detail="策略类型不匹配")
    
    try:
        result = strategy.update()
        return StrategyResponse(
            strategy_id=strategy_id,
            status=result.get('status', 'updated'),
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sliding-window-grid/{strategy_id}/status")
async def get_sliding_window_grid_strategy_status(strategy_id: str):
    """获取滑动窗口网格策略状态"""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    strategy = _strategies[strategy_id]
    if not isinstance(strategy, SlidingWindowGridStrategy):
        raise HTTPException(status_code=400, detail="策略类型不匹配")
    
    try:
        status = strategy.get_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """删除策略（无论类型）"""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    strategy = _strategies[strategy_id]
    
    try:
        # 如果策略正在运行，先停止
        if strategy.is_running:
            strategy.stop()
        
        # 从字典中删除策略
        del _strategies[strategy_id]
        
        return {
            "status": "deleted",
            "strategy_id": strategy_id,
            "message": "策略已删除"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除策略失败: {str(e)}")

