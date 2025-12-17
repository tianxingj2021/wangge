"""
交易所相关API
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from decimal import Decimal
import time
from backend.models.schemas import BalanceResponse
from exchanges.factory import ExchangeFactory
from core.config_manager import get_config_manager
from core.exchange_pool import ExchangeInstancePool
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/exchange", tags=["交易所"])


def create_exchange_instance(config: Dict[str, Any]):
    """根据配置创建交易所实例"""
    if not config or not config.get('name') or not config.get('api_key'):
        raise ValueError("配置不完整：缺少name或api_key")
    
    try:
        kwargs = {
            'testnet': config.get('testnet', False)
        }
        
        # Extended交易所需要额外参数
        if config['name'].lower() == 'extended':
            if config.get('public_key'):
                kwargs['public_key'] = config['public_key']
            if config.get('private_key'):
                kwargs['private_key'] = config['private_key']
            elif config.get('secret_key'):
                kwargs['private_key'] = config['secret_key']
            if config.get('vault') is not None:
                kwargs['vault'] = config['vault']
            if config.get('default_market'):
                kwargs['default_market'] = config['default_market']
        
        exchange = ExchangeFactory.create(
            name=config['name'],
            api_key=config['api_key'],
            secret_key=config.get('secret_key', ''),
            **kwargs
        )
        return exchange
    except Exception as e:
        raise ValueError(f"交易所初始化失败: {str(e)}")


def get_exchange_instance(exchange_name: Optional[str] = None):
    """获取交易所实例（支持依赖注入和直接调用，使用实例池复用）"""
    config_manager = get_config_manager()
    
    # 获取配置并确定account_key
    if exchange_name:
        # 获取指定交易所的配置
        config = config_manager.get_exchange_config(exchange_name)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"交易所 {exchange_name} 的配置不存在"
            )
        account_key = config.get('account_key', exchange_name)
    else:
        # 向后兼容：获取第一个配置
        config = config_manager.get_config()
        if not config or not config.get('name') or not config.get('api_key'):
            raise HTTPException(
                status_code=400,
                detail="交易所未配置，请先在前端配置交易所API密钥"
            )
        account_key = config.get('account_key', config.get('name', 'default').lower())
    
    # 尝试从实例池获取（复用实例，避免重复初始化）
    # 使用get_managers确保线程安全，避免并发创建多个实例
    try:
        # 先尝试获取已存在的实例
        exchange = ExchangeInstancePool.get_exchange(account_key)
        if exchange:
            return exchange
        
        # 如果不存在，通过get_managers创建（线程安全）
        # 这会确保即使并发请求，也只会创建一个实例
        managers = ExchangeInstancePool.get_managers(account_key)
        exchange = ExchangeInstancePool.get_exchange(account_key)
        if exchange:
            return exchange
    except Exception as e:
        # 如果从池中获取失败，记录错误但继续尝试创建
        logger.warning(f"[Exchange] 从实例池获取失败: {e}", exc_info=True)
    
    # 如果池中没有，创建新实例（兜底方案）
    try:
        exchange = create_exchange_instance(config)
        # 将实例加入池中（如果还没有）
        with ExchangeInstancePool._lock:
            if account_key not in ExchangeInstancePool._instances:
                ExchangeInstancePool._instances[account_key] = exchange
        return exchange
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_default_exchange_instance():
    """获取默认交易所实例（用于依赖注入）"""
    return get_exchange_instance(None)


@router.get("/list")
async def list_exchanges():
    """获取支持的交易所列表"""
    exchanges = ExchangeFactory.list_exchanges()
    return {"exchanges": exchanges}


# 余额缓存（30秒TTL）
_balance_cache: Dict[str, Dict[str, Any]] = {}
_balance_cache_time: Dict[str, float] = {}
_balance_cache_lock = None
def _get_cache_lock():
    global _balance_cache_lock
    if _balance_cache_lock is None:
        import threading
        _balance_cache_lock = threading.Lock()
    return _balance_cache_lock

@router.get("/balance")
async def get_balance(currency: str = None, exchange_name: Optional[str] = None):
    """获取账户余额（支持指定交易所名称，带缓存机制）"""
    # 生成缓存键
    cache_key = f"{exchange_name or 'default'}:{currency or 'all'}"
    cache_ttl = 30  # 30秒缓存
    
    # 检查缓存
    with _get_cache_lock():
        if cache_key in _balance_cache and cache_key in _balance_cache_time:
            cache_age = time.time() - _balance_cache_time[cache_key]
            if cache_age < cache_ttl:
                # 返回缓存数据
                cached_balance = _balance_cache[cache_key]
                return BalanceResponse(**cached_balance)
    
    try:
        exchange = get_exchange_instance(exchange_name)
        balance = exchange.get_balance(currency)
        
        # 处理Extended返回的格式（可能包含balances数组）
        result = None
        if isinstance(balance, dict):
            # 如果返回的是所有余额（包含balances数组），转换为标准格式
            if 'balances' in balance and 'total_wallet_balance' in balance:
                # Extended格式：返回主要余额或第一个资产
                if balance.get('balances') and len(balance['balances']) > 0:
                    main_balance = balance['balances'][0]
                    result = BalanceResponse(
                        currency=main_balance.get('currency', 'all'),
                        available=main_balance.get('available', '0'),
                        frozen=main_balance.get('frozen', '0'),
                        total=main_balance.get('total', '0')
                    )
                else:
                    # 使用总余额
                    result = BalanceResponse(
                        currency=balance.get('currency', 'all'),
                        available=balance.get('available_balance', '0'),
                        frozen=str(Decimal(balance.get('total_wallet_balance', '0')) - Decimal(balance.get('available_balance', '0'))),
                        total=balance.get('total_wallet_balance', '0')
                    )
            else:
                # 标准格式
                result = BalanceResponse(**balance)
        else:
            raise ValueError("余额数据格式不正确")
        
        # 更新缓存
        if result:
            with _get_cache_lock():
                _balance_cache[cache_key] = {
                    'currency': result.currency,
                    'available': result.available,
                    'frozen': result.frozen,
                    'total': result.total
                }
                _balance_cache_time[cache_key] = time.time()
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balances", response_model=Dict[str, Any])
async def get_all_balances():
    """获取所有已配置交易所的余额"""
    config_manager = get_config_manager()
    all_exchanges = config_manager.get_all_exchanges()
    
    if not all_exchanges:
        return {
            "balances": [],
            "count": 0
        }
    
    balances_list = []
    # 这里使用 ExchangeInstancePool 复用已初始化的交易所实例，避免每次请求都重新初始化
    for exchange_name, exchange_config in all_exchanges.items():
        try:
            # exchange_name 实际上是 account_key（见 ConfigManager.get_all_exchanges）
            account_key = exchange_config.get('account_key', exchange_name)
            
            # 优先从实例池获取（启动时已经初始化过）
            exchange = ExchangeInstancePool.get_exchange(account_key)
            if not exchange:
                # 如果实例不存在，通过 get_managers 创建并放入实例池
                managers = ExchangeInstancePool.get_managers(account_key)
                # managers[1] 是 AccountManager，可以后续用来做更细致的缓存
                exchange = ExchangeInstancePool.get_exchange(account_key)
            
            if not exchange:
                raise ValueError(f"无法获取交易所实例: {account_key}")
            
            balance_data = exchange.get_balance()
            
            # 处理余额数据格式
            if isinstance(balance_data, dict):
                # Extended格式：包含balances数组
                if 'balances' in balance_data and 'total_wallet_balance' in balance_data:
                    balances_list.append({
                        "exchange_name": exchange_name,
                        "display_name": exchange_config.get('name', exchange_name).capitalize(),
                        "testnet": exchange_config.get('testnet', False),
                        "balance": {
                            "currency": "all",
                            "available": balance_data.get('available_balance', '0'),
                            "frozen": str(Decimal(balance_data.get('total_wallet_balance', '0')) - Decimal(balance_data.get('available_balance', '0'))),
                            "total": balance_data.get('total_wallet_balance', '0'),
                            "balances": balance_data.get('balances', [])
                        },
                        "status": "success"
                    })
                else:
                    # 标准格式
                    balances_list.append({
                        "exchange_name": exchange_name,
                        "display_name": exchange_config.get('name', exchange_name).capitalize(),
                        "testnet": exchange_config.get('testnet', False),
                        "balance": balance_data,
                        "status": "success"
                    })
            else:
                balances_list.append({
                    "exchange_name": exchange_name,
                    "display_name": exchange_config.get('name', exchange_name).capitalize(),
                    "testnet": exchange_config.get('testnet', False),
                    "balance": None,
                    "status": "error",
                    "error": "余额数据格式不正确"
                })
        except Exception as e:
            balances_list.append({
                "exchange_name": exchange_name,
                "display_name": exchange_config.get('name', exchange_name).capitalize(),
                "testnet": exchange_config.get('testnet', False),
                "balance": None,
                "status": "error",
                "error": str(e)
            })
    
    return {
        "balances": balances_list,
        "count": len(balances_list)
    }


@router.get("/ticker/{symbol}")
async def get_ticker(symbol: str, exchange=Depends(get_default_exchange_instance)):
    """获取交易对价格"""
    try:
        ticker = exchange.get_ticker(symbol)
        return ticker
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

