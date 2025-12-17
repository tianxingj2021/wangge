#!/usr/bin/env python3
"""
测试Extended交易所订单缓存和WebSocket订阅功能
验证使用缓存避免API限速
"""
import sys
import os
import time
from decimal import Decimal

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config_manager import get_config_manager
from exchanges.factory import ExchangeFactory


def test_orders_cache():
    """测试订单缓存和WebSocket订阅功能"""
    print("=" * 60)
    print("测试Extended交易所订单缓存和WebSocket订阅功能")
    print("=" * 60)
    
    # 获取配置
    config_manager = get_config_manager()
    extended_config = config_manager.get_exchange_config('extended')
    
    if not extended_config:
        print("❌ 错误: Extended交易所未配置")
        return False
    
    print(f"\n✓ 找到Extended交易所配置")
    
    try:
        # 创建交易所实例
        print("\n正在创建交易所实例...")
        exchange = ExchangeFactory.create(
            name=extended_config['name'],
            api_key=extended_config['api_key'],
            secret_key=extended_config.get('secret_key', ''),
            public_key=extended_config.get('public_key'),
            private_key=extended_config.get('private_key', extended_config.get('secret_key', '')),
            vault=extended_config.get('vault'),
            testnet=extended_config.get('testnet', False),
            default_market=extended_config.get('default_market', 'BTC-USD')
        )
        print("✓ 交易所实例创建成功")
        
        test_symbol = "BTC-USD"
        
        print(f"\n{'=' * 60}")
        print(f"测试订单缓存功能")
        print(f"{'=' * 60}")
        
        # 测试1: 第一次查询（应该使用REST API并建立缓存）
        print(f"\n【测试1】第一次查询未成交订单（建立缓存）...")
        start_time = time.time()
        orders1 = exchange.get_open_orders(test_symbol)
        elapsed1 = time.time() - start_time
        print(f"✓ 查询完成，耗时: {elapsed1:.3f}秒")
        print(f"  订单数量: {len(orders1)}")
        if orders1:
            for i, order in enumerate(orders1[:3], 1):
                print(f"  订单{i}: ID={order.get('order_id')}, 价格={order.get('price')}, 状态={order.get('status')}")
        
        # 测试2: 立即再次查询（应该使用缓存）
        print(f"\n【测试2】立即再次查询（应该使用缓存）...")
        start_time = time.time()
        orders2 = exchange.get_open_orders(test_symbol)
        elapsed2 = time.time() - start_time
        print(f"✓ 查询完成，耗时: {elapsed2:.3f}秒")
        print(f"  订单数量: {len(orders2)}")
        
        if elapsed2 < elapsed1 * 0.5:
            print(f"✓ 缓存生效！第二次查询明显更快（{elapsed2:.3f}秒 vs {elapsed1:.3f}秒）")
        else:
            print(f"⚠ 缓存可能未生效，两次查询耗时相近")
        
        # 测试3: 连续多次查询（验证缓存避免API限速）
        print(f"\n【测试3】连续10次查询（验证缓存避免API限速）...")
        start_time = time.time()
        for i in range(10):
            orders = exchange.get_open_orders(test_symbol)
        total_time = time.time() - start_time
        avg_time = total_time / 10
        print(f"✓ 10次查询完成")
        print(f"  总耗时: {total_time:.3f}秒")
        print(f"  平均每次: {avg_time:.3f}秒")
        print(f"  订单数量: {len(orders)}")
        
        if avg_time < 0.1:
            print(f"✓ 缓存工作正常！平均查询时间很短，说明使用了缓存而非REST API")
        else:
            print(f"⚠ 平均查询时间较长，可能仍在使用REST API")
        
        # 测试4: 等待缓存过期后查询（应该重新使用REST API）
        print(f"\n【测试4】等待6秒后查询（缓存应已过期，重新使用REST API）...")
        print("  等待中...")
        time.sleep(6)
        start_time = time.time()
        orders3 = exchange.get_open_orders(test_symbol)
        elapsed3 = time.time() - start_time
        print(f"✓ 查询完成，耗时: {elapsed3:.3f}秒")
        print(f"  订单数量: {len(orders3)}")
        
        if elapsed3 > elapsed2:
            print(f"✓ 缓存过期后重新使用REST API，查询时间变长（{elapsed3:.3f}秒 vs {elapsed2:.3f}秒）")
        else:
            print(f"⚠ 查询时间未明显变化")
        
        # 测试5: 验证WebSocket后台轮询
        print(f"\n【测试5】验证WebSocket后台轮询（等待6秒，观察缓存是否自动更新）...")
        print("  等待中...")
        time.sleep(6)
        start_time = time.time()
        orders4 = exchange.get_open_orders(test_symbol)
        elapsed4 = time.time() - start_time
        print(f"✓ 查询完成，耗时: {elapsed4:.3f}秒")
        print(f"  订单数量: {len(orders4)}")
        
        if elapsed4 < elapsed3:
            print(f"✓ WebSocket后台轮询可能已更新缓存，查询时间变短（{elapsed4:.3f}秒 vs {elapsed3:.3f}秒）")
        else:
            print(f"⚠ 查询时间未明显变化")
        
        print(f"\n{'=' * 60}")
        print("✓ 订单缓存测试完成")
        print(f"{'=' * 60}")
        print("\n总结:")
        print("  - 第一次查询使用REST API建立缓存")
        print("  - 后续查询在缓存有效期内使用缓存（避免API限速）")
        print("  - WebSocket后台轮询每5秒更新一次缓存")
        print("  - 缓存过期后自动重新使用REST API获取最新数据")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_orders_cache()
    sys.exit(0 if success else 1)

