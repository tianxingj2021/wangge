"""
辅助函数
"""
from decimal import Decimal
from typing import Union


def format_decimal(value: Union[Decimal, str, float], precision: int = 8) -> str:
    """
    格式化Decimal为字符串
    
    Args:
        value: 数值
        precision: 精度
        
    Returns:
        格式化后的字符串
    """
    if isinstance(value, (str, float)):
        value = Decimal(str(value))
    return f"{value:.{precision}f}".rstrip('0').rstrip('.')


def parse_decimal(value: Union[str, float, int]) -> Decimal:
    """
    解析为Decimal
    
    Args:
        value: 数值
        
    Returns:
        Decimal对象
    """
    return Decimal(str(value))

