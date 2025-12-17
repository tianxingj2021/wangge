"""
配置管理器
管理交易所配置的保存和读取
"""
import json
import os
from typing import Optional, Dict, Any
from pathlib import Path


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config/exchange_config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config: Optional[Dict[str, Any]] = None
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        if self._config is not None:
            return self._config
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                self._config = {}
        else:
            self._config = {}
        
        return self._config
    
    def _save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"保存配置文件失败: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置（向后兼容：返回第一个配置或空字典）
        
        Returns:
            配置字典
        """
        config = self._load_config()
        # 如果是旧格式（直接包含name和api_key），返回原格式
        if config and 'name' in config and 'api_key' in config:
            return config.copy()
        # 如果是新格式（字典的字典），返回第一个配置
        if isinstance(config, dict) and config:
            for exchange_name, exchange_config in config.items():
                if isinstance(exchange_config, dict) and exchange_config.get('name') and exchange_config.get('api_key'):
                    return exchange_config.copy()
        return {}
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置（向后兼容：如果config包含name，则保存为单个交易所配置）
        
        Args:
            config: 配置字典
            
        Returns:
            是否保存成功
        """
        try:
            # 如果配置包含name，保存为单个交易所配置
            if 'name' in config:
                exchange_name = config['name'].lower()
                all_configs = self._load_config()
                # 如果是旧格式，转换为新格式
                if all_configs and 'name' in all_configs and 'api_key' in all_configs:
                    old_config = all_configs
                    all_configs = {old_config['name'].lower(): old_config}
                all_configs[exchange_name] = config.copy()
                self._config = all_configs
            else:
                # 否则直接保存整个配置字典
                self._config = config.copy()
            self._save_config()
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def save_exchange_config(self, exchange_name: str, config: Dict[str, Any]) -> bool:
        """
        保存单个交易所配置
        
        Args:
            exchange_name: 交易所名称
            config: 配置字典
            
        Returns:
            是否保存成功
        """
        try:
            all_configs = self._load_config()
            # 如果是旧格式，转换为新格式
            if all_configs and 'name' in all_configs and 'api_key' in all_configs:
                old_config = all_configs
                all_configs = {old_config['name'].lower(): old_config}
            # 确保配置中包含交易所名称
            config['name'] = exchange_name.lower()
            
            # 生成account_key（如果不存在）
            if 'account_key' not in config:
                # 使用exchange_name作为account_key（向后兼容）
                # 如果有account_alias，可以基于它生成更友好的key
                account_key = exchange_name.lower()
                # 如果已有相同exchange_name的配置，添加序号
                counter = 1
                while account_key in all_configs:
                    account_key = f"{exchange_name.lower()}_{counter}"
                    counter += 1
                config['account_key'] = account_key
            else:
                account_key = config['account_key']
            
            # 如果没有account_alias，生成一个默认的
            if 'account_alias' not in config:
                exchange_display = exchange_name.capitalize()
                config['account_alias'] = f"{exchange_display}账号"
            
            # 使用account_key作为存储键（而不是exchange_name）
            all_configs[account_key] = config.copy()
            self._config = all_configs
            self._save_config()
            return True
        except Exception as e:
            print(f"保存交易所配置失败: {e}")
            return False
    
    def get_exchange_config(self, exchange_name: str) -> Optional[Dict[str, Any]]:
        """
        获取单个交易所配置（向后兼容：支持通过exchange_name查找）
        
        Args:
            exchange_name: 交易所名称或account_key
            
        Returns:
            配置字典，如果不存在返回None
        """
        all_configs = self._load_config()
        # 如果是旧格式，检查是否匹配
        if all_configs and 'name' in all_configs and 'api_key' in all_configs:
            if all_configs['name'].lower() == exchange_name.lower():
                config = all_configs.copy()
                if 'account_key' not in config:
                    config['account_key'] = config['name'].lower()
                if 'account_alias' not in config:
                    config['account_alias'] = f"{config['name'].capitalize()}账号"
                return config
            return None
        # 新格式：先尝试作为account_key查找
        if exchange_name in all_configs:
            config = all_configs[exchange_name].copy()
            if 'account_key' not in config:
                config['account_key'] = exchange_name
            if 'account_alias' not in config:
                config['account_alias'] = f"{config.get('name', 'Unknown').capitalize()}账号"
            return config
        # 如果作为account_key找不到，尝试通过exchange_name查找
        exchange_name_lower = exchange_name.lower()
        for account_key, config in all_configs.items():
            if isinstance(config, dict) and config.get('name', '').lower() == exchange_name_lower:
                result = config.copy()
                if 'account_key' not in result:
                    result['account_key'] = account_key
                if 'account_alias' not in result:
                    result['account_alias'] = f"{result['name'].capitalize()}账号"
                return result
        return None
    
    def get_all_exchanges(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有已配置的交易所（向后兼容：返回account_key作为key）
        
        Returns:
            字典，key为account_key，value为配置字典
        """
        all_configs = self._load_config()
        # 如果是旧格式，转换为新格式
        if all_configs and 'name' in all_configs and 'api_key' in all_configs:
            old_config = all_configs.copy()
            # 为旧配置生成account_key
            if 'account_key' not in old_config:
                old_config['account_key'] = old_config['name'].lower()
            if 'account_alias' not in old_config:
                old_config['account_alias'] = f"{old_config['name'].capitalize()}账号"
            return {old_config['account_key']: old_config}
        # 新格式：只返回有效的配置（包含name和api_key）
        result = {}
        for account_key, exchange_config in all_configs.items():
            if isinstance(exchange_config, dict) and exchange_config.get('name') and exchange_config.get('api_key'):
                # 确保有account_key和account_alias
                config = exchange_config.copy()
                if 'account_key' not in config:
                    config['account_key'] = account_key
                if 'account_alias' not in config:
                    config['account_alias'] = f"{config['name'].capitalize()}账号"
                result[account_key] = config
        return result
    
    def get_account_config(self, account_key: str) -> Optional[Dict[str, Any]]:
        """
        根据account_key获取账号配置
        
        Args:
            account_key: 账号唯一标识
            
        Returns:
            配置字典，如果不存在返回None
        """
        all_configs = self._load_config()
        # 如果是旧格式，检查是否匹配
        if all_configs and 'name' in all_configs and 'api_key' in all_configs:
            if all_configs.get('account_key', all_configs['name'].lower()) == account_key:
                config = all_configs.copy()
                if 'account_key' not in config:
                    config['account_key'] = account_key
                if 'account_alias' not in config:
                    config['account_alias'] = f"{config['name'].capitalize()}账号"
                return config
            return None
        # 新格式
        if account_key in all_configs:
            config = all_configs[account_key].copy()
            if 'account_key' not in config:
                config['account_key'] = account_key
            if 'account_alias' not in config:
                config['account_alias'] = f"{config.get('name', 'Unknown').capitalize()}账号"
            return config
        return None
    
    def delete_account_config(self, account_key: str) -> bool:
        """
        删除账号配置
        
        Args:
            account_key: 账号唯一标识
            
        Returns:
            是否删除成功
        """
        try:
            all_configs = self._load_config()
            # 如果是旧格式，检查是否匹配
            if all_configs and 'name' in all_configs and 'api_key' in all_configs:
                old_account_key = all_configs.get('account_key', all_configs['name'].lower())
                if old_account_key == account_key:
                    self._config = {}
                    self._save_config()
                    return True
                return False
            # 新格式
            if account_key in all_configs:
                del all_configs[account_key]
                self._config = all_configs
                self._save_config()
                return True
            return False
        except Exception as e:
            print(f"删除账号配置失败: {e}")
            return False
    
    def delete_exchange_config(self, exchange_name: str) -> bool:
        """
        删除单个交易所配置
        
        Args:
            exchange_name: 交易所名称
            
        Returns:
            是否删除成功
        """
        try:
            all_configs = self._load_config()
            # 如果是旧格式，检查是否匹配
            if all_configs and 'name' in all_configs and 'api_key' in all_configs:
                if all_configs['name'].lower() == exchange_name.lower():
                    self._config = {}
                    self._save_config()
                    return True
                return False
            # 新格式
            exchange_name_lower = exchange_name.lower()
            if exchange_name_lower in all_configs:
                del all_configs[exchange_name_lower]
                self._config = all_configs
                self._save_config()
                return True
            return False
        except Exception as e:
            print(f"删除交易所配置失败: {e}")
            return False
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """
        更新配置（部分更新，向后兼容）
        
        Args:
            updates: 要更新的配置项
            
        Returns:
            是否更新成功
        """
        try:
            config = self._load_config()
            # 如果是旧格式，直接更新
            if config and 'name' in config and 'api_key' in config:
                config.update(updates)
                self._config = config
            else:
                # 新格式：如果updates包含name，更新对应交易所
                if 'name' in updates:
                    exchange_name = updates['name'].lower()
                    if exchange_name in config:
                        config[exchange_name].update(updates)
                        self._config = config
                    else:
                        # 如果不存在，创建新配置
                        config[exchange_name] = updates.copy()
                        self._config = config
                else:
                    # 否则更新所有配置（向后兼容）
                    config.update(updates)
                    self._config = config
            self._save_config()
            return True
        except Exception as e:
            print(f"更新配置失败: {e}")
            return False
    
    def clear_config(self) -> bool:
        """
        清空所有配置
        
        Returns:
            是否清空成功
        """
        try:
            self._config = {}
            self._save_config()
            return True
        except Exception as e:
            print(f"清空配置失败: {e}")
            return False
    
    def has_config(self) -> bool:
        """
        检查是否有配置
        
        Returns:
            是否有配置
        """
        config = self._load_config()
        # 旧格式检查
        if config and 'name' in config and 'api_key' in config:
            return True
        # 新格式检查
        return len(self.get_all_exchanges()) > 0


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例（单例）"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

