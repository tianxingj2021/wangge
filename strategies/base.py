"""
策略基类
定义所有交易策略必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.order_manager import OrderManager
from core.account_manager import AccountManager
from core.position_manager import PositionManager


class BaseStrategy(ABC):
    """策略抽象基类"""
    
    def __init__(
        self,
        order_manager: OrderManager,
        account_manager: AccountManager,
        position_manager: PositionManager,
        account_key: Optional[str] = None,
        **kwargs
    ):
        """
        初始化策略
        
        Args:
            order_manager: 订单管理器
            account_manager: 账户管理器
            position_manager: 持仓管理器
            account_key: 账号唯一标识
            **kwargs: 策略特定参数
        """
        self.order_manager = order_manager
        self.account_manager = account_manager
        self.position_manager = position_manager
        self.account_key = account_key
        self.is_running = False
        self.config = kwargs
    
    @abstractmethod
    def start(self) -> Dict[str, Any]:
        """
        启动策略
        
        Returns:
            启动结果
        """
        pass
    
    @abstractmethod
    def stop(self) -> Dict[str, Any]:
        """
        停止策略
        
        Returns:
            停止结果
        """
        pass
    
    @abstractmethod
    def update(self) -> Dict[str, Any]:
        """
        更新策略状态（定期调用）
        
        Returns:
            更新结果
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        获取策略状态
        
        Returns:
            策略状态信息
        """
        pass
    
    def validate_config(self) -> bool:
        """
        验证策略配置（子类可重写）
        
        Returns:
            配置是否有效
        """
        return True

