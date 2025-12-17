"""
交易所接口测试
"""
import pytest
from exchanges.base import BaseExchange
from exchanges.factory import ExchangeFactory


def test_exchange_factory():
    """测试交易所工厂"""
    exchanges = ExchangeFactory.list_exchanges()
    assert 'binance' in exchanges


def test_binance_exchange_creation():
    """测试创建币安交易所实例"""
    exchange = ExchangeFactory.create(
        name='binance',
        api_key='test_key',
        secret_key='test_secret',
        testnet=True
    )
    assert exchange is not None
    assert exchange.name == 'BinanceExchange'

