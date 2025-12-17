"""
订单相关API
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from backend.models.schemas import OrderRequest, OrderResponse
from exchanges.factory import ExchangeFactory
from core.order_manager import OrderManager
from core.config_manager import get_config_manager

router = APIRouter(prefix="/order", tags=["订单"])


def get_order_manager():
    """获取订单管理器（依赖注入）"""
    config_manager = get_config_manager()
    config = config_manager.get_config()
    
    if not config or not config.get('name') or not config.get('api_key'):
        raise HTTPException(
            status_code=400,
            detail="交易所未配置，请先在前端配置交易所API密钥"
        )
    
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
        return OrderManager(exchange)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"订单管理器初始化失败: {str(e)}")


@router.post("/place", response_model=OrderResponse)
async def place_order(request: OrderRequest, order_manager=Depends(get_order_manager)):
    """下单"""
    try:
        from decimal import Decimal
        
        result = order_manager.place_order(
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=Decimal(request.quantity),
            price=Decimal(request.price) if request.price else None
        )
        return OrderResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel/{symbol}/{order_id}")
async def cancel_order(symbol: str, order_id: str, order_manager=Depends(get_order_manager)):
    """取消订单"""
    try:
        result = order_manager.cancel_order(symbol, order_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/{order_id}")
async def get_order(symbol: str, order_id: str, order_manager=Depends(get_order_manager)):
    """查询订单"""
    try:
        order = order_manager.get_order(symbol, order_id)
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/open/{symbol}")
async def get_open_orders(symbol: str, order_manager=Depends(get_order_manager)):
    """获取未成交订单列表"""
    try:
        orders = order_manager.get_open_orders(symbol)
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

