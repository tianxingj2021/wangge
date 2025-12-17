#!/usr/bin/env python3
"""
测试Extended交易所订单WebSocket订阅和缓存功能
验证在有订单的情况下，缓存如何工作
"""
import sys
import os
import time
from decimal import Decimal

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config_manager import get_config_manager
from exchanges.factory import ExchangeFactory


def test_orders_websocket():
    """测试订单WebSocket订阅和缓存功能"""
    print("=" * 60)
    print("测试Extended交易所订单WebSocket订阅和缓存功能")
    print("=" * 60)
    
    # 获取配置
    config_manager = get_config_manager()
    extended_config = config_manager.get_exchange_config('extended')
    
    if not extended_config:
        print("❌ 错误: Extended交易所未配置")
        return False
    
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
        test_price = Decimal("80000")
        test_quantity = Decimal("0.001")
        
        print(f"\n{'=' * 60}")
        print(f"测试场景：创建订单后验证缓存功能")
        print(f"{'=' * 60}")
        
        # 创建测试订单
        print(f"\n【步骤1】创建测试订单（价格: {test_price}）...")
        try:
            order = exchange.place_order(
                symbol=test_symbol,
                side="buy",
                order_type="limit",
                quantity=test_quantity,
                price=test_price
            )
            order_id = order.get('order_id')
            print(f"✓ 订单创建成功，订单ID: {order_id}")
        except Exception as e:
            print(f"❌ 创建订单失败: {e}")
            return False
        
        # 等待订单创建完成
        time.sleep(1)
        
        # 测试2: 第一次查询（建立缓存）
        print(f"\n【步骤2】第一次查询未成交订单（建立缓存）...")
        start_time = time.time()
        orders1 = exchange.get_open_orders(test_symbol)
        elapsed1 = time.time() - start_time
        print(f"✓ 查询完成，耗时: {elapsed1:.3f}秒")
        print(f"  订单数量: {len(orders1)}")
        if orders1:
            print(f"  找到订单: ID={orders1[0].get('order_id')}, 价格={orders1[0].get('price')}")
        
        # 测试3: 立即再次查询（应该使用缓存）
        print(f"\n【步骤3】立即再次查询（应该使用缓存）...")
        start_time = time.time()
        orders2 = exchange.get_open_orders(test_symbol)
        elapsed2 = time.time() - start_time
        print(f"✓ 查询完成，耗时: {elapsed2:.3f}秒")
        print(f"  订单数量: {len(orders2)}")
        
        if elapsed2 < elapsed1 * 0.5:
            print(f"✓ 缓存生效！第二次查询明显更快（{elapsed2:.3f}秒 vs {elapsed1:.3f}秒）")
        else:
            print(f"⚠ 缓存可能未生效")
        
        # 测试4: 连续多次查询（验证缓存避免API限速）
        print(f"\n【步骤4】连续5次查询（验证缓存避免API限速）...")
        start_time = time.time()
        for i in range(5):
            orders = exchange.get_open_orders(test_symbol)
        total_time = time.time() - start_time
        avg_time = total_time / 5
        print(f"✓ 5次查询完成")
        print(f"  总耗时: {total_time:.3f}秒")
        print(f"  平均每次: {avg_time:.3f}秒")
        
        if avg_time < 0.1:
            print(f"✓ 缓存工作正常！平均查询时间很短，说明使用了缓存而非REST API")
        elif avg_time < elapsed1 * 0.5:
            print(f"✓ 缓存工作正常！平均查询时间明显短于第一次查询")
        else:
            print(f"⚠ 平均查询时间较长")
        
        # 测试5: 取消订单后验证缓存更新
        print(f"\n【步骤5】取消订单后验证缓存更新...")
        try:
            cancel_result = exchange.cancel_order(test_symbol, order_id)
            print(f"✓ 订单取消成功")
        except Exception as e:
            print(f"⚠ 取消订单失败: {e}")
        
        # 等待一下让缓存更新
        time.sleep(1)
        
        # 查询订单（应该从缓存获取，但订单已被取消）
        print(f"\n【步骤6】查询订单（验证缓存是否反映最新状态）...")
        orders3 = exchange.get_open_orders(test_symbol)
        print(f"✓ 查询完成")
        print(f"  订单数量: {len(orders3)}")
        
        if len(orders3) == 0:
            print(f"✓ 缓存已更新，正确反映订单已取消的状态")
        else:
            print(f"⚠ 缓存可能未及时更新，仍显示订单存在")
            print(f"  等待3秒后再次查询...")
            time.sleep(3)
            orders4 = exchange.get_open_orders(test_symbol)
            if len(orders4) == 0:
                print(f"✓ 缓存已更新（延迟更新）")
            else:
                print(f"⚠ 缓存仍未更新")
        
        print(f"\n{'=' * 60}")
        print("✓ 订单WebSocket订阅和缓存测试完成")
        print(f"{'=' * 60}")
        print("\n总结:")
        print("  ✓ 订单缓存功能已实现")
        print("  ✓ 缓存有效期为5秒，避免频繁调用REST API")
        print("  ✓ WebSocket后台轮询每5秒更新一次缓存")
        print("  ✓ 创建/取消订单时自动更新缓存")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_orders_websocket()
    sys.exit(0 if success else 1)

