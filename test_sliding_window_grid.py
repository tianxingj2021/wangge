#!/usr/bin/env python3
"""
测试滑动窗口网格策略
"""
import sys
import os
import time
from decimal import Decimal

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config_manager import get_config_manager
from exchanges.factory import ExchangeFactory
from core.order_manager import OrderManager
from core.account_manager import AccountManager
from core.position_manager import PositionManager
from strategies.sliding_window_grid import SlidingWindowGridStrategy


def test_sliding_window_grid():
    """测试滑动窗口网格策略"""
    print("=" * 60)
    print("测试滑动窗口网格策略")
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
        
        # 创建管理器
        order_manager = OrderManager(exchange)
        account_manager = AccountManager(exchange)
        position_manager = PositionManager(exchange)
        
        # 创建策略实例
        test_symbol = "BTC-USD"
        order_size = Decimal("0.001")  # 每单0.001 BTC
        
        print(f"\n创建滑动窗口网格策略...")
        print(f"  交易对: {test_symbol}")
        print(f"  每单数量: {order_size}")
        
        strategy = SlidingWindowGridStrategy(
            order_manager=order_manager,
            account_manager=account_manager,
            position_manager=position_manager,
            symbol=test_symbol,
            order_size=order_size
        )
        
        # 显示配置
        print(f"\n策略配置:")
        print(f"  总订单数: {strategy.GRID_CONFIG['TOTAL_ORDERS']}")
        print(f"  窗口宽度: {strategy.GRID_CONFIG['WINDOW_PERCENT'] * 100}%")
        print(f"  卖单比例: {strategy.GRID_CONFIG['SELL_RATIO'] * 100}%")
        print(f"  买单比例: {strategy.GRID_CONFIG['BUY_RATIO'] * 100}%")
        print(f"  价格间距: {strategy.GRID_CONFIG['BASE_PRICE_INTERVAL']}")
        print(f"  安全偏移: {strategy.GRID_CONFIG['SAFE_GAP']}")
        
        # 启动策略
        print(f"\n启动策略...")
        start_result = strategy.start()
        print(f"启动结果: {start_result}")
        
        if start_result.get('status') != 'started':
            print(f"❌ 策略启动失败")
            return False
        
        # 执行几次更新循环
        print(f"\n执行策略更新循环...")
        for i in range(3):
            print(f"\n--- 第 {i+1} 次更新 ---")
            update_result = strategy.update()
            print(f"更新结果: {update_result}")
            
            # 获取状态
            status = strategy.get_status()
            print(f"策略状态:")
            print(f"  运行中: {status['is_running']}")
            print(f"  循环次数: {status['cycle_count']}")
            print(f"  活跃订单: {status['active_orders']}")
            print(f"  当前价格: {status['current_price']}")
            print(f"  持仓: {status['position_btc']} BTC")
            
            if i < 2:  # 最后一次不需要等待
                print(f"等待5秒后继续...")
                time.sleep(5)
        
        # 停止策略
        print(f"\n停止策略...")
        stop_result = strategy.stop()
        print(f"停止结果: {stop_result}")
        
        print(f"\n{'=' * 60}")
        print("✓ 滑动窗口网格策略测试完成")
        print(f"{'=' * 60}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_sliding_window_grid()
    sys.exit(0 if success else 1)

