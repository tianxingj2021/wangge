"""
WebSocket API - 实时推送策略状态
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Set
import asyncio
import json
from backend.api.strategy import _strategies
from strategies.sliding_window_grid import SlidingWindowGridStrategy

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# 存储所有WebSocket连接
active_connections: Dict[str, Set[WebSocket]] = {}


async def broadcast_strategy_status(strategy_id: str, status: dict):
    """向所有订阅该策略的WebSocket连接广播状态"""
    if strategy_id in active_connections:
        disconnected = set()
        for websocket in active_connections[strategy_id]:
            try:
                await websocket.send_json(status)
            except Exception as e:
                print(f"WebSocket发送失败: {e}")
                disconnected.add(websocket)
        
        # 移除断开的连接
        active_connections[strategy_id] -= disconnected


@router.websocket("/strategy/{strategy_id}")
async def websocket_strategy_status(websocket: WebSocket, strategy_id: str):
    """WebSocket端点：实时推送策略状态"""
    await websocket.accept()
    
    # 验证策略是否存在
    if strategy_id not in _strategies:
        await websocket.send_json({
            "error": "策略不存在",
            "strategy_id": strategy_id
        })
        await websocket.close()
        return
    
    strategy = _strategies[strategy_id]
    if not isinstance(strategy, SlidingWindowGridStrategy):
        await websocket.send_json({
            "error": "策略类型不匹配",
            "strategy_id": strategy_id
        })
        await websocket.close()
        return
    
    # 添加到连接列表
    if strategy_id not in active_connections:
        active_connections[strategy_id] = set()
    active_connections[strategy_id].add(websocket)
    
    try:
        # 立即发送一次当前状态
        status = strategy.get_status()
        await websocket.send_json({
            "type": "status",
            "strategy_id": strategy_id,
            "data": status
        })
        
        # 定期推送状态更新（每2秒）
        while True:
            await asyncio.sleep(2)
            
            # 检查策略是否还存在
            if strategy_id not in _strategies:
                await websocket.send_json({
                    "type": "error",
                    "message": "策略已删除"
                })
                break
            
            # 获取最新状态
            status = strategy.get_status()
            await websocket.send_json({
                "type": "status",
                "strategy_id": strategy_id,
                "data": status
            })
            
    except WebSocketDisconnect:
        print(f"WebSocket断开连接: {strategy_id}")
    except Exception as e:
        print(f"WebSocket错误: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # 从连接列表中移除
        if strategy_id in active_connections:
            active_connections[strategy_id].discard(websocket)
            if not active_connections[strategy_id]:
                del active_connections[strategy_id]

