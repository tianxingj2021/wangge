#!/usr/bin/env python3
"""
测试Extended交易所限价挂单功能
测试以80000价格买入BTC
"""
import sys
import os
import time
from decimal import Decimal

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config_manager import get_config_manager
from exchanges.factory import ExchangeFactory


def test_extended_limit_order():
    """测试Extended交易所限价挂单功能"""
    print("=" * 60)
    print("测试Extended交易所限价挂单功能")
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
        test_price = Decimal("80000")  # 限价80000
        test_quantity = Decimal("0.001")  # 买入0.001 BTC
        
        print(f"\n{'=' * 60}")
        print(f"测试限价挂单")
        print(f"{'=' * 60}")
        print(f"交易对: {test_symbol}")
        print(f"方向: 买入 (BUY)")
        print(f"订单类型: 限价单 (LIMIT)")
        print(f"价格: {test_price}")
        print(f"数量: {test_quantity} BTC")
        print(f"{'=' * 60}")
        
        # 先获取当前价格，确认80000是否合理
        print("\n【步骤1】获取当前BTC价格...")
        try:
            ticker = exchange.get_ticker(test_symbol)
            current_price = float(ticker.get('price', 0))
            bid_price = float(ticker.get('bid', 0))
            ask_price = float(ticker.get('ask', 0))
            
            print(f"✓ 当前价格信息:")
            print(f"  最新价格: {current_price}")
            print(f"  买1价格: {bid_price}")
            print(f"  卖1价格: {ask_price}")
            print(f"  挂单价格: {test_price}")
            
            # 检查价格是否合理（80000应该远低于当前价格，适合买入限价单）
            if test_price < current_price:
                print(f"\n✓ 挂单价格 {test_price} 低于当前价格 {current_price}，适合买入限价单")
            else:
                print(f"\n⚠ 警告: 挂单价格 {test_price} 高于或等于当前价格 {current_price}")
                print(f"  这可能导致订单立即成交或无法成交")
                confirm = input("  是否继续？(y/n): ")
                if confirm.lower() != 'y':
                    print("取消测试")
                    return False
        except Exception as e:
            print(f"⚠ 获取价格失败: {e}，继续测试...")
        
        # 测试下单
        print(f"\n【步骤2】提交限价买入订单...")
        try:
            order_result = exchange.place_order(
                symbol=test_symbol,
                side="buy",
                order_type="limit",
                quantity=test_quantity,
                price=test_price
            )
            
            print(f"✓ 订单提交成功!")
            print(f"\n订单详情:")
            print(f"  订单ID: {order_result.get('order_id', 'N/A')}")
            print(f"  交易对: {order_result.get('symbol', 'N/A')}")
            print(f"  方向: {order_result.get('side', 'N/A')}")
            print(f"  类型: {order_result.get('type', 'N/A')}")
            print(f"  数量: {order_result.get('quantity', 'N/A')}")
            print(f"  价格: {order_result.get('price', 'N/A')}")
            print(f"  状态: {order_result.get('status', 'N/A')}")
            print(f"  时间类型: {order_result.get('time_in_force', 'N/A')}")
            print(f"  已成交数量: {order_result.get('executed_qty', 'N/A')}")
            print(f"  平均成交价: {order_result.get('avg_price', 'N/A')}")
            print(f"  下单时间: {order_result.get('time', 'N/A')}")
            
            order_id = order_result.get('order_id')
            
            # 等待一下，然后查询订单状态
            print(f"\n【步骤3】等待2秒后查询订单状态...")
            time.sleep(2)
            
            try:
                order_info = exchange.get_order(test_symbol, order_id)
                print(f"✓ 订单查询成功:")
                print(f"  订单ID: {order_info.get('order_id', 'N/A')}")
                print(f"  状态: {order_info.get('status', 'N/A')}")
                print(f"  数量: {order_info.get('quantity', 'N/A')}")
                print(f"  价格: {order_info.get('price', 'N/A')}")
                print(f"  已成交数量: {order_info.get('executed_qty', 'N/A')}")
                print(f"  平均成交价: {order_info.get('avg_price', 'N/A')}")
                
                status = order_info.get('status', '').upper()
                if status == 'NEW':
                    print(f"\n✓ 订单状态: NEW (已挂单，等待成交)")
                elif status == 'FILLED':
                    print(f"\n✓ 订单状态: FILLED (已完全成交)")
                elif status == 'PARTIALLY_FILLED':
                    print(f"\n✓ 订单状态: PARTIALLY_FILLED (部分成交)")
                elif status == 'CANCELLED':
                    print(f"\n⚠ 订单状态: CANCELLED (已取消)")
                else:
                    print(f"\n订单状态: {status}")
                    
            except Exception as e:
                print(f"⚠ 查询订单状态失败: {e}")
            
            # 询问是否取消订单
            print(f"\n【步骤4】订单管理选项")
            print(f"订单已成功提交，订单ID: {order_id}")
            print(f"如果需要取消订单，可以运行:")
            print(f"  exchange.cancel_order('{test_symbol}', '{order_id}')")
            
            # 非交互式环境，自动取消测试订单
            cancel = 'y'  # 自动取消测试订单
            print(f"\n自动取消测试订单...")
            if cancel.lower() == 'y':
                try:
                    cancel_result = exchange.cancel_order(test_symbol, order_id)
                    print(f"✓ 订单取消成功:")
                    print(f"  订单ID: {cancel_result.get('order_id', 'N/A')}")
                    print(f"  状态: {cancel_result.get('status', 'N/A')}")
                except Exception as e:
                    print(f"❌ 取消订单失败: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"订单保留，请稍后手动取消")
            
            print(f"\n{'=' * 60}")
            print("✓ 限价挂单测试完成")
            print(f"{'=' * 60}")
            return True
            
        except Exception as e:
            print(f"❌ 下单失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_extended_limit_order()
    sys.exit(0 if success else 1)

