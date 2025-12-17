#!/usr/bin/env python3
"""
测试Extended交易所同时挂多个限价单功能
测试同时挂80000和75000的买入订单，然后单独取消75000的订单
"""
import sys
import os
import time
from decimal import Decimal

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config_manager import get_config_manager
from exchanges.factory import ExchangeFactory


def test_multiple_orders():
    """测试同时挂多个限价单"""
    print("=" * 60)
    print("测试Extended交易所同时挂多个限价单功能")
    print("=" * 60)
    
    # 获取配置
    config_manager = get_config_manager()
    extended_config = config_manager.get_exchange_config('extended')
    
    if not extended_config:
        print("❌ 错误: Extended交易所未配置")
        print("请先在前端配置Extended交易所API密钥")
        return False
    
    print(f"\n✓ 找到Extended交易所配置")
    print(f"  交易所名称: {extended_config.get('name', 'extended')}")
    print(f"  测试网: {extended_config.get('testnet', False)}")
    
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
        
        # 测试参数
        test_symbol = "BTC-USD"
        test_quantity = Decimal("0.001")  # 每个订单买入0.001 BTC
        
        # 两个限价单的价格
        price1 = Decimal("80000")
        price2 = Decimal("75000")
        
        print(f"\n{'=' * 60}")
        print(f"测试同时挂多个限价单")
        print(f"{'=' * 60}")
        print(f"交易对: {test_symbol}")
        print(f"方向: 买入 (BUY)")
        print(f"订单类型: 限价单 (LIMIT)")
        print(f"\n订单1: 价格 {price1}, 数量 {test_quantity} BTC")
        print(f"订单2: 价格 {price2}, 数量 {test_quantity} BTC")
        print(f"{'=' * 60}")
        
        # 先获取当前价格
        print("\n【步骤1】获取当前BTC价格...")
        try:
            ticker = exchange.get_ticker(test_symbol)
            current_price = float(ticker.get('price', 0))
            print(f"✓ 当前价格: {current_price}")
            print(f"  挂单价格1: {price1} (低于当前价 {current_price - float(price1):.2f})")
            print(f"  挂单价格2: {price2} (低于当前价 {current_price - float(price2):.2f})")
        except Exception as e:
            print(f"⚠ 获取价格失败: {e}，继续测试...")
        
        # 提交第一个订单（80000）
        print(f"\n【步骤2】提交第一个限价买入订单（价格: {price1}）...")
        order1 = None
        try:
            order1 = exchange.place_order(
                symbol=test_symbol,
                side="buy",
                order_type="limit",
                quantity=test_quantity,
                price=price1
            )
            print(f"✓ 订单1提交成功!")
            print(f"  订单ID: {order1.get('order_id', 'N/A')}")
            print(f"  价格: {order1.get('price', 'N/A')}")
            print(f"  数量: {order1.get('quantity', 'N/A')}")
            print(f"  状态: {order1.get('status', 'N/A')}")
        except Exception as e:
            print(f"❌ 订单1提交失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 等待一小段时间
        print("\n等待1秒...")
        time.sleep(1)
        
        # 提交第二个订单（75000）
        print(f"\n【步骤3】提交第二个限价买入订单（价格: {price2}）...")
        order2 = None
        try:
            order2 = exchange.place_order(
                symbol=test_symbol,
                side="buy",
                order_type="limit",
                quantity=test_quantity,
                price=price2
            )
            print(f"✓ 订单2提交成功!")
            print(f"  订单ID: {order2.get('order_id', 'N/A')}")
            print(f"  价格: {order2.get('price', 'N/A')}")
            print(f"  数量: {order2.get('quantity', 'N/A')}")
            print(f"  状态: {order2.get('status', 'N/A')}")
        except Exception as e:
            print(f"❌ 订单2提交失败: {e}")
            import traceback
            traceback.print_exc()
            # 如果第二个订单失败，取消第一个订单
            if order1:
                print(f"\n尝试取消订单1...")
                try:
                    exchange.cancel_order(test_symbol, order1.get('order_id'))
                    print(f"✓ 订单1已取消")
                except:
                    pass
            return False
        
        # 等待一小段时间
        print("\n等待2秒后查询所有未成交订单...")
        time.sleep(2)
        
        # 查询所有未成交订单
        print(f"\n【步骤4】查询所有未成交订单...")
        try:
            open_orders = exchange.get_open_orders(test_symbol)
            print(f"✓ 当前未成交订单数量: {len(open_orders)}")
            for i, order in enumerate(open_orders, 1):
                print(f"\n  订单{i}:")
                print(f"    订单ID: {order.get('order_id', 'N/A')}")
                print(f"    价格: {order.get('price', 'N/A')}")
                print(f"    数量: {order.get('quantity', 'N/A')}")
                print(f"    方向: {order.get('side', 'N/A')}")
                print(f"    状态: {order.get('status', 'N/A')}")
        except Exception as e:
            print(f"⚠ 查询未成交订单失败: {e}")
        
        # 取消第二个订单（75000）
        order2_id = order2.get('order_id')
        print(f"\n【步骤5】单独取消订单2（价格: {price2}, 订单ID: {order2_id}）...")
        try:
            cancel_result = exchange.cancel_order(test_symbol, order2_id)
            print(f"✓ 订单2取消成功!")
            print(f"  订单ID: {cancel_result.get('order_id', 'N/A')}")
            print(f"  状态: {cancel_result.get('status', 'N/A')}")
        except Exception as e:
            print(f"❌ 取消订单2失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 等待一小段时间
        print("\n等待2秒后再次查询未成交订单...")
        time.sleep(2)
        
        # 再次查询未成交订单，确认订单2已取消
        print(f"\n【步骤6】再次查询未成交订单，确认订单2已取消...")
        try:
            open_orders = exchange.get_open_orders(test_symbol)
            print(f"✓ 当前未成交订单数量: {len(open_orders)}")
            
            # 检查订单1是否还在
            order1_id = order1.get('order_id')
            order1_found = False
            order2_found = False
            
            for order in open_orders:
                oid = order.get('order_id')
                if oid == order1_id:
                    order1_found = True
                    print(f"\n✓ 订单1（价格: {price1}）仍在未成交订单中:")
                    print(f"    订单ID: {oid}")
                    print(f"    价格: {order.get('price', 'N/A')}")
                    print(f"    状态: {order.get('status', 'N/A')}")
                elif oid == order2_id:
                    order2_found = True
                    print(f"\n⚠ 订单2（价格: {price2}）仍在未成交订单中（取消可能失败）")
            
            if not order1_found:
                print(f"\n⚠ 订单1（价格: {price1}）不在未成交订单中（可能已成交或被取消）")
            
            if not order2_found:
                print(f"\n✓ 订单2（价格: {price2}）已成功取消，不在未成交订单中")
            
            # 总结
            print(f"\n{'=' * 60}")
            print("测试总结:")
            print(f"  订单1（价格: {price1}）: {'仍在' if order1_found else '不在'}未成交订单中")
            print(f"  订单2（价格: {price2}）: {'仍在' if order2_found else '已取消'}未成交订单中")
            print(f"{'=' * 60}")
            
        except Exception as e:
            print(f"⚠ 查询未成交订单失败: {e}")
        
        # 询问是否取消订单1
        order1_id = order1.get('order_id') if order1 else None
        if order1_id:
            print(f"\n【步骤7】订单管理")
            print(f"订单1（价格: {price1}, 订单ID: {order1_id}）仍在未成交订单中")
            print(f"如果需要取消订单1，可以运行:")
            print(f"  exchange.cancel_order('{test_symbol}', '{order1_id}')")
            
            # 自动取消订单1（测试清理）
            print(f"\n自动取消订单1（测试清理）...")
            try:
                cancel_result = exchange.cancel_order(test_symbol, order1_id)
                print(f"✓ 订单1取消成功!")
                print(f"  订单ID: {cancel_result.get('order_id', 'N/A')}")
                print(f"  状态: {cancel_result.get('status', 'N/A')}")
            except Exception as e:
                print(f"⚠ 取消订单1失败: {e}")
        
        print(f"\n{'=' * 60}")
        print("✓ 多订单测试完成")
        print(f"{'=' * 60}")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_multiple_orders()
    sys.exit(0 if success else 1)

