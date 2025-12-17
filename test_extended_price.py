#!/usr/bin/env python3
"""
测试Extended交易所获取BTC价格功能
测试最新价格、买1价格、卖1价格，并验证WebSocket实时价格
"""
import sys
import os
import time
from decimal import Decimal

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config_manager import get_config_manager
from exchanges.factory import ExchangeFactory


def test_extended_price():
    """测试Extended交易所价格获取"""
    print("=" * 60)
    print("测试Extended交易所BTC价格获取功能")
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
    print(f"  默认交易对: {extended_config.get('default_market', 'BTC-USD')}")
    
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
        
        # 测试交易对
        test_symbol = "BTC-USD"
        print(f"\n{'=' * 60}")
        print(f"测试交易对: {test_symbol}")
        print(f"{'=' * 60}")
        
        # 测试1: 获取Ticker（包含最新价格、买1、卖1）
        print("\n【测试1】获取Ticker数据（包含最新价格、买1、卖1）...")
        try:
            ticker = exchange.get_ticker(test_symbol)
            print(f"✓ Ticker获取成功:")
            print(f"  交易对: {ticker.get('symbol', 'N/A')}")
            print(f"  最新价格: {ticker.get('price', 'N/A')}")
            print(f"  买1价格: {ticker.get('bid', 'N/A')}")
            print(f"  卖1价格: {ticker.get('ask', 'N/A')}")
            print(f"  买1数量: {ticker.get('bid_qty', 'N/A')}")
            print(f"  卖1数量: {ticker.get('ask_qty', 'N/A')}")
            print(f"  24h最高: {ticker.get('high', 'N/A')}")
            print(f"  24h最低: {ticker.get('low', 'N/A')}")
            print(f"  24h成交量: {ticker.get('volume', 'N/A')}")
            print(f"  24h成交额: {ticker.get('quote_volume', 'N/A')}")
            print(f"  24h涨跌: {ticker.get('price_change', 'N/A')}")
            print(f"  24h涨跌幅: {ticker.get('price_change_percent', 'N/A')}%")
            
            # 验证价格数据
            if ticker.get('price') and ticker.get('bid') and ticker.get('ask'):
                price = float(ticker.get('price', 0))
                bid = float(ticker.get('bid', 0))
                ask = float(ticker.get('ask', 0))
                
                if price > 0 and bid > 0 and ask > 0:
                    if bid <= price <= ask or abs(bid - price) < price * 0.1 or abs(ask - price) < price * 0.1:
                        print(f"\n✓ 价格验证通过: 买1({bid}) <= 最新价({price}) <= 卖1({ask})")
                    else:
                        print(f"\n⚠ 价格验证警告: 买1({bid}) 和 卖1({ask}) 与最新价({price})差异较大")
                else:
                    print(f"\n❌ 价格验证失败: 价格数据异常")
            else:
                print(f"\n❌ 价格验证失败: 缺少价格数据")
                
        except Exception as e:
            print(f"❌ Ticker获取失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 测试2: 获取订单簿（验证WebSocket数据）
        print(f"\n【测试2】获取订单簿数据（验证WebSocket实时价格）...")
        try:
            orderbook = exchange.get_orderbook(test_symbol, limit=5)
            print(f"✓ 订单簿获取成功:")
            print(f"  交易对: {orderbook.get('symbol', 'N/A')}")
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            print(f"\n  买盘（前5档）:")
            for i, bid in enumerate(bids[:5], 1):
                print(f"    {i}. 价格: {bid[0]}, 数量: {bid[1]}")
            
            print(f"\n  卖盘（前5档）:")
            for i, ask in enumerate(asks[:5], 1):
                print(f"    {i}. 价格: {ask[0]}, 数量: {ask[1]}")
            
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                spread = best_ask - best_bid
                spread_percent = (spread / best_bid) * 100 if best_bid > 0 else 0
                
                print(f"\n  买1价格: {best_bid}")
                print(f"  卖1价格: {best_ask}")
                print(f"  价差: {spread:.2f} ({spread_percent:.4f}%)")
                
                # 验证买1和卖1价格与Ticker中的一致
                ticker_bid = float(ticker.get('bid', 0))
                ticker_ask = float(ticker.get('ask', 0))
                
                if abs(best_bid - ticker_bid) < 0.01 and abs(best_ask - ticker_ask) < 0.01:
                    print(f"\n✓ 买1和卖1价格与Ticker一致")
                else:
                    print(f"\n⚠ 买1和卖1价格与Ticker不一致:")
                    print(f"  Ticker买1: {ticker_bid}, 订单簿买1: {best_bid}")
                    print(f"  Ticker卖1: {ticker_ask}, 订单簿卖1: {best_ask}")
            else:
                print(f"\n❌ 订单簿数据为空")
                
        except Exception as e:
            print(f"❌ 订单簿获取失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 测试3: 实时价格更新测试（验证WebSocket实时性）
        print(f"\n【测试3】实时价格更新测试（验证WebSocket实时性）...")
        try:
            print("  获取初始价格...")
            ticker1 = exchange.get_ticker(test_symbol)
            initial_price = float(ticker1.get('price', 0))
            initial_bid = float(ticker1.get('bid', 0))
            initial_ask = float(ticker1.get('ask', 0))
            print(f"  初始价格: {initial_price}, 买1: {initial_bid}, 卖1: {initial_ask}")
            
            print("  等待5秒后再次获取价格...")
            time.sleep(5)
            
            ticker2 = exchange.get_ticker(test_symbol)
            updated_price = float(ticker2.get('price', 0))
            updated_bid = float(ticker2.get('bid', 0))
            updated_ask = float(ticker2.get('ask', 0))
            print(f"  更新价格: {updated_price}, 买1: {updated_bid}, 卖1: {updated_ask}")
            
            price_change = abs(updated_price - initial_price)
            bid_change = abs(updated_bid - initial_bid)
            ask_change = abs(updated_ask - initial_ask)
            
            print(f"\n  价格变化:")
            print(f"    最新价变化: {price_change:.2f}")
            print(f"    买1变化: {bid_change:.2f}")
            print(f"    卖1变化: {ask_change:.2f}")
            
            if price_change > 0 or bid_change > 0 or ask_change > 0:
                print(f"\n✓ 价格已更新，WebSocket实时价格功能正常")
            else:
                print(f"\n⚠ 价格未变化（可能是市场波动较小）")
                
        except Exception as e:
            print(f"❌ 实时价格更新测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print(f"\n{'=' * 60}")
        print("✓ 所有测试完成")
        print(f"{'=' * 60}")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_extended_price()
    sys.exit(0 if success else 1)

