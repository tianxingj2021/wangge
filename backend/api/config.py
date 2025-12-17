"""
配置管理API
用于前端配置交易所API密钥
"""
from fastapi import APIRouter, HTTPException
from backend.models.schemas import ExchangeConfig
from core.config_manager import get_config_manager
from exchanges.factory import ExchangeFactory
from typing import Dict, Any, List

router = APIRouter(prefix="/config", tags=["配置"])


@router.get("/exchange", response_model=ExchangeConfig)
async def get_exchange_config():
    """获取当前交易所配置（向后兼容：返回第一个配置）"""
    config_manager = get_config_manager()
    config = config_manager.get_config()
    
    if not config:
        # 返回空配置
        return ExchangeConfig(
            name="",
            api_key="",
            secret_key="",
            testnet=False
        )
    
    return ExchangeConfig(**config)


@router.get("/exchanges", response_model=Dict[str, Any])
async def get_all_exchanges():
    """获取所有已配置的交易所列表（账号列表）"""
    config_manager = get_config_manager()
    all_exchanges = config_manager.get_all_exchanges()
    
    # 返回账号列表，每个包含账号标识和基本信息
    exchanges_list = []
    for account_key, exchange_config in all_exchanges.items():
        exchanges_list.append({
            "name": account_key,  # 使用account_key作为name（向后兼容）
            "account_key": account_key,
            "account_alias": exchange_config.get('account_alias', account_key),
            "exchange_name": exchange_config.get('name', ''),
            "display_name": exchange_config.get('account_alias') or exchange_config.get('name', account_key).capitalize(),
            "testnet": exchange_config.get('testnet', False),
            "has_api_key": bool(exchange_config.get('api_key'))
        })
    
    return {
        "exchanges": exchanges_list,
        "count": len(exchanges_list)
    }


@router.get("/exchange/{exchange_name}", response_model=ExchangeConfig)
async def get_exchange_config_by_name(exchange_name: str):
    """获取指定交易所的配置（支持account_key或exchange_name）"""
    config_manager = get_config_manager()
    
    # 先尝试作为account_key查找
    config = config_manager.get_account_config(exchange_name)
    
    # 如果找不到，尝试作为exchange_name查找
    if not config:
        config = config_manager.get_exchange_config(exchange_name)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"交易所 {exchange_name} 的配置不存在")
    
    return ExchangeConfig(**config)


@router.post("/exchange", response_model=Dict[str, Any])
async def save_exchange_config(config: ExchangeConfig):
    """保存交易所配置"""
    config_manager = get_config_manager()
    
    # 转换为字典
    config_dict = config.model_dump(exclude_none=True)
    exchange_name = config.name.lower()
    
    # 如果提供了account_alias，确保它被保存
    if config.account_alias:
        config_dict['account_alias'] = config.account_alias.strip()
    
    # 保存配置
    success = config_manager.save_exchange_config(exchange_name, config_dict)
    
    if not success:
        raise HTTPException(status_code=500, detail="保存配置失败")
    
    # 获取保存后的account_key
    saved_config = config_manager.get_exchange_config(exchange_name)
    account_key = saved_config.get('account_key') if saved_config else None
    
    return {
        "status": "success",
        "message": "配置保存成功",
        "exchange_name": exchange_name,
        "account_key": account_key
    }


@router.delete("/exchange/{exchange_name}", response_model=Dict[str, Any])
async def delete_exchange_config(exchange_name: str):
    """删除指定交易所的配置（支持account_key）"""
    from core.exchange_pool import ExchangeInstancePool
    
    config_manager = get_config_manager()
    
    # 先获取配置，确定account_key
    config = config_manager.get_exchange_config(exchange_name)
    account_key = None
    if config:
        account_key = config.get('account_key', exchange_name)
    
    # 删除配置
    success = config_manager.delete_exchange_config(exchange_name)
    
    if not success:
        # 如果通过exchange_name删除失败，尝试通过account_key删除
        if account_key and account_key != exchange_name:
            success = config_manager.delete_account_config(account_key)
            if success:
                account_key_to_remove = account_key
            else:
                raise HTTPException(status_code=404, detail=f"交易所 {exchange_name} 的配置不存在")
        else:
            raise HTTPException(status_code=404, detail=f"交易所 {exchange_name} 的配置不存在")
    else:
        account_key_to_remove = account_key or exchange_name
    
    # 从实例池中移除
    if account_key_to_remove:
        ExchangeInstancePool.remove_account(account_key_to_remove)
    
    return {
        "status": "success",
        "message": f"交易所 {exchange_name} 的配置已删除"
    }


@router.post("/exchange/test", response_model=Dict[str, Any])
async def test_exchange_connection(config: ExchangeConfig):
    """测试交易所连接"""
    try:
        # 构建参数
        kwargs = {
            'testnet': config.testnet
        }
        
        # Extended交易所需要额外参数
        if config.name.lower() == 'extended':
            if not config.public_key:
                return {
                    "status": "error",
                    "message": "Extended交易所需要提供公钥(Public Key)"
                }
            if config.vault is None:
                return {
                    "status": "error",
                    "message": "Extended交易所需要提供金库ID(Vault ID)"
                }
            
            if config.public_key:
                kwargs['public_key'] = config.public_key
            if config.private_key:
                kwargs['private_key'] = config.private_key
            elif config.secret_key:
                kwargs['private_key'] = config.secret_key
            if config.vault is not None:
                kwargs['vault'] = config.vault
            if config.default_market:
                kwargs['default_market'] = config.default_market
        
        # 创建交易所实例
        try:
            exchange = ExchangeFactory.create(
                name=config.name,
                api_key=config.api_key,
                secret_key=config.secret_key,
                **kwargs
            )
        except ImportError as e:
            return {
                "status": "error",
                "message": f"交易所SDK未安装: {str(e)}"
            }
        except ValueError as e:
            return {
                "status": "error",
                "message": f"配置错误: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"创建交易所实例失败: {str(e)}"
            }
        
        # 测试连接：尝试获取余额或市场信息
        try:
            # 对于Extended，需要先初始化
            if hasattr(exchange, 'extended_client'):
                import asyncio
                import threading
                import queue
                import traceback
                
                result_queue = queue.Queue()
                
                def init_in_thread():
                    """在线程中运行异步初始化"""
                    # 创建新的事件循环（在线程中）
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        # 运行初始化（测试连接时强制重新创建 trading_client，不启动 OrderBook 事件循环）
                        new_loop.run_until_complete(
                            exchange.extended_client.initialize(
                                start_orderbook_loop=False,
                                force_recreate=True
                            )
                        )
                        result_queue.put(('success', None))
                    except Exception as e:
                        # 捕获详细的错误信息
                        error_trace = traceback.format_exc()
                        error_info = {
                            'error': str(e),
                            'type': type(e).__name__,
                            'traceback': error_trace
                        }
                        result_queue.put(('error', error_info))
                    finally:
                        # 清理事件循环
                        try:
                            # 取消所有待处理的任务
                            pending = asyncio.all_tasks(new_loop)
                            for task in pending:
                                task.cancel()
                            if pending:
                                new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except Exception:
                            pass
                        try:
                            new_loop.close()
                        except Exception:
                            pass
                
                # 在后台线程中运行初始化
                thread = threading.Thread(target=init_in_thread, daemon=True)
                thread.start()
                thread.join(timeout=20)  # 增加超时时间到20秒
                
                if not result_queue.empty():
                    status, result = result_queue.get()
                    if status == 'error':
                        # 解析错误信息
                        if isinstance(result, dict):
                            error_msg = result.get('error', '未知错误')
                            error_type = result.get('type', '')
                            
                            # 根据错误类型提供友好的错误信息
                            if 'Connection' in error_type or 'timeout' in error_msg.lower() or '网络' in error_msg:
                                error_msg = f"网络连接失败: {error_msg}。请检查：1) 网络连接是否正常 2) API配置是否正确 3) 是否使用了正确的测试网/主网设置"
                            elif 'Authentication' in error_type or '401' in error_msg or '403' in error_msg:
                                error_msg = f"认证失败: {error_msg}。请检查API密钥、公钥、私钥是否正确"
                            elif 'ValueError' in error_type or 'vault' in error_msg.lower():
                                error_msg = f"配置错误: {error_msg}。请检查所有必填字段是否已填写"
                            elif 'ImportError' in error_type:
                                error_msg = f"SDK错误: {error_msg}。请确保Extended SDK已正确安装"
                            else:
                                error_msg = f"初始化失败: {error_msg}"
                        else:
                            error_msg = str(result)
                        
                        return {
                            "status": "error",
                            "message": error_msg
                        }
                else:
                    return {
                        "status": "error",
                        "message": "初始化超时（20秒），请检查：1) 网络连接 2) API配置 3) Extended服务器是否可访问"
                    }
                
                # 等待一小段时间确保初始化完成
                import time
                time.sleep(0.5)
            
            # 尝试获取市场列表或余额
            if hasattr(exchange, 'get_balance'):
                # 直接调用get_balance，它内部会处理异步操作
                try:
                    balance = exchange.get_balance()
                    return {
                        "status": "success",
                        "message": "连接成功",
                        "data": {
                            "balance_available": True,
                            "balance": balance
                        }
                    }
                except Exception as e:
                    error_msg = str(e)
                    # 提供更友好的错误信息
                    if "Event loop is closed" in error_msg:
                        error_msg = "事件循环错误，请重试。如果问题持续，请检查Extended SDK配置。"
                    elif "初始化" in error_msg:
                        error_msg = f"初始化失败: {error_msg}"
                    elif "网络" in error_msg or "Connection" in error_msg:
                        error_msg = f"网络连接失败: {error_msg}。请检查网络和API配置。"
                    
                    return {
                        "status": "error",
                        "message": f"获取余额失败: {error_msg}"
                    }
            else:
                return {
                    "status": "success",
                    "message": "连接成功（无法测试余额）"
                }
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            # 提供更友好的错误信息
            if "SDK未安装" in error_msg or "x10-python-trading-starknet" in error_msg:
                error_msg = "Extended SDK未安装，请运行: pip install x10-python-trading-starknet"
            elif "未初始化" in error_msg or "Event loop is closed" in error_msg:
                error_msg = "交易所客户端初始化失败，请检查配置和网络连接"
            elif "网络" in error_msg or "timeout" in error_msg.lower() or "Connection" in error_msg:
                error_msg = "网络连接失败，请检查：1) 网络连接 2) API配置 3) Extended服务器是否可访问"
            elif "Event loop" in error_msg:
                error_msg = "异步操作失败，请重试或检查配置"
            
            return {
                "status": "error",
                "message": f"连接测试失败: {error_msg}"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"测试连接失败: {str(e)}"
        }


@router.delete("/exchange", response_model=Dict[str, Any])
async def clear_exchange_config():
    """清空交易所配置"""
    config_manager = get_config_manager()
    success = config_manager.clear_config()
    
    if not success:
        raise HTTPException(status_code=500, detail="清空配置失败")
    
    return {
        "status": "success",
        "message": "配置已清空"
    }

