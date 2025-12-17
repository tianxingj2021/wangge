"""
交易所实例池
管理交易所实例的创建和复用，避免重复创建连接
"""
from typing import Dict, Tuple, Optional
from threading import Lock
from exchanges.base import BaseExchange
from exchanges.factory import ExchangeFactory
from core.order_manager import OrderManager
from core.account_manager import AccountManager
from core.position_manager import PositionManager
from core.config_manager import get_config_manager
from utils.logger import get_logger

logger = get_logger(__name__)


class ExchangeInstancePool:
    """交易所实例池（单例）"""
    
    _instances: Dict[str, BaseExchange] = {}
    _managers: Dict[str, Tuple[OrderManager, AccountManager, PositionManager]] = {}
    _lock = Lock()
    
    @classmethod
    def get_managers(cls, account_key: str) -> Tuple[OrderManager, AccountManager, PositionManager]:
        """
        获取管理器实例（从池中获取或创建）
        
        Args:
            account_key: 账号唯一标识
            
        Returns:
            (OrderManager, AccountManager, PositionManager) 元组
            
        Raises:
            ValueError: 如果账号配置不存在或创建失败
        """
        with cls._lock:
            # 如果已存在，直接返回
            if account_key in cls._managers:
                return cls._managers[account_key]
            
            # 获取账号配置
            config_manager = get_config_manager()
            config = config_manager.get_account_config(account_key)
            
            if not config:
                raise ValueError(f"账号配置不存在: {account_key}")
            
            if not config.get('name') or not config.get('api_key'):
                raise ValueError(f"账号配置不完整: {account_key}")
            
            # 创建交易所实例
            try:
                exchange_name = config.get('name', 'Unknown')
                testnet = config.get('testnet', False)
                logger.info(f"[ExchangePool] 正在创建交易所实例: {exchange_name} (account_key: {account_key}, testnet: {testnet})")
                
                kwargs = {
                    'testnet': testnet
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
                
                logger.info(f"[ExchangePool] 交易所实例创建成功: {exchange_name} (account_key: {account_key})")
                
                # 保存实例
                cls._instances[account_key] = exchange
                
                # 创建管理器
                logger.debug(f"[ExchangePool] 正在创建管理器: {account_key}")
                order_manager = OrderManager(exchange)
                account_manager = AccountManager(exchange)
                position_manager = PositionManager(exchange)
                
                managers = (order_manager, account_manager, position_manager)
                cls._managers[account_key] = managers
                
                logger.info(f"[ExchangePool] 管理器创建完成: {account_key}")
                return managers
                
            except Exception as e:
                logger.error(f"[ExchangePool] 创建交易所实例失败: {account_key}, 错误: {str(e)}", exc_info=True)
                raise ValueError(f"创建交易所实例失败: {str(e)}")
    
    @classmethod
    def get_exchange(cls, account_key: str) -> Optional[BaseExchange]:
        """
        获取交易所实例（如果不存在则创建）
        
        Args:
            account_key: 账号唯一标识
            
        Returns:
            交易所实例，如果不存在返回None
        """
        with cls._lock:
            if account_key in cls._instances:
                return cls._instances[account_key]
            
            # 如果不存在，尝试创建（通过get_managers）
            try:
                cls.get_managers(account_key)
                return cls._instances.get(account_key)
            except Exception:
                return None
    
    @classmethod
    def remove_account(cls, account_key: str) -> bool:
        """
        移除账号的实例（当账号配置被删除时调用）
        
        Args:
            account_key: 账号唯一标识
            
        Returns:
            是否移除成功
        """
        with cls._lock:
            removed = False
            if account_key in cls._instances:
                try:
                    # 尝试关闭交易所连接
                    exchange = cls._instances[account_key]
                    if hasattr(exchange, 'close'):
                        logger.info(f"[ExchangePool] 正在关闭交易所连接: {account_key}")
                        exchange.close()
                        logger.info(f"[ExchangePool] 交易所连接已关闭: {account_key}")
                except Exception as e:
                    logger.error(f"[ExchangePool] 关闭交易所连接失败: {account_key}, 错误: {str(e)}", exc_info=True)
                del cls._instances[account_key]
                removed = True
            
            if account_key in cls._managers:
                del cls._managers[account_key]
                removed = True
            
            return removed
    
    @classmethod
    def clear(cls):
        """清空所有实例（用于测试或重启）"""
        with cls._lock:
            for account_key, exchange in list(cls._instances.items()):
                try:
                    if hasattr(exchange, 'close'):
                        exchange.close()
                except Exception:
                    pass
            cls._instances.clear()
            cls._managers.clear()
    
    @classmethod
    def list_accounts(cls) -> list:
        """
        获取所有已缓存的账号列表
        
        Returns:
            账号key列表
        """
        with cls._lock:
            return list(cls._instances.keys())

