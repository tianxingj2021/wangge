# Extended交易所集成说明

## 概述

Extended交易所已成功集成到网格交易系统中。Extended是一个基于StarkNet的永续合约交易所，使用x10-python-trading-starknet SDK。

## 配置说明

### 1. 安装依赖

Extended交易所需要额外的SDK：

```bash
pip install x10-python-trading-starknet
```

### 2. 环境变量配置

在 `.env` 文件中配置Extended交易所：

```env
# 交易所名称
EXCHANGE_NAME=extended

# Extended必需参数
EXCHANGE_API_KEY=your_api_key
EXCHANGE_SECRET_KEY=your_private_key  # Extended的私钥
EXCHANGE_PUBLIC_KEY=your_public_key    # Extended的公钥（十六进制字符串）
EXCHANGE_VAULT=your_vault_id           # 金库ID（整数）

# 可选参数
EXCHANGE_TESTNET=true                  # 是否使用测试网
EXCHANGE_DEFAULT_MARKET=BTC-USD       # 默认交易对
```

### 3. 参数说明

- **api_key**: Extended API密钥
- **secret_key/private_key**: StarkNet私钥（十六进制字符串）
- **public_key**: StarkNet公钥（十六进制字符串）
- **vault**: 金库ID（整数）
- **testnet**: 是否使用测试网（true/false）
- **default_market**: 默认交易对（如 BTC-USD）

## 交易对格式

Extended使用 `-` 分隔的交易对格式，例如：
- `BTC-USD`（不是 `BTC/USDT`）
- `ETH-USD`

系统会自动转换常见的交易对格式：
- `BTC/USDT` → `BTC-USD`
- `ETH/USDT` → `ETH-USD`

## 功能支持

Extended交易所支持以下功能：

✅ **已实现**:
- 获取账户余额
- 获取交易对价格（Ticker）
- 获取订单簿（深度）
- 下单（限价单、市价单）
- 取消订单
- 查询订单
- 获取未成交订单列表

⚠️ **部分支持**:
- K线数据（Extended暂不支持，返回空列表）

## 使用示例

### 通过API使用

```python
from exchanges.factory import ExchangeFactory

# 创建Extended交易所实例
exchange = ExchangeFactory.create(
    name='extended',
    api_key='your_api_key',
    secret_key='your_private_key',
    public_key='your_public_key',
    vault=12345,
    testnet=True
)

# 获取余额
balance = exchange.get_balance()

# 获取价格
ticker = exchange.get_ticker('BTC-USD')

# 下单
order = exchange.place_order(
    symbol='BTC-USD',
    side='buy',
    order_type='limit',
    quantity=Decimal('0.01'),
    price=Decimal('50000')
)
```

### 通过REST API使用

启动服务后，可以通过REST API使用：

```bash
# 获取余额
curl http://localhost:8000/api/v1/exchange/balance

# 获取价格
curl http://localhost:8000/api/v1/exchange/ticker/BTC-USD

# 下单
curl -X POST http://localhost:8000/api/v1/order/place \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC-USD",
    "side": "buy",
    "order_type": "limit",
    "quantity": "0.01",
    "price": "50000"
  }'
```

## 注意事项

1. **异步适配**: Extended SDK是异步的，但我们的系统使用同步接口。系统会自动处理异步/同步转换。

2. **初始化**: Extended客户端需要异步初始化。系统会在第一次调用时自动初始化。

3. **事件循环**: 如果当前线程已有事件循环在运行，系统会使用线程池执行异步操作。

4. **错误处理**: 如果Extended SDK未安装或初始化失败，会抛出相应的异常。

5. **测试网**: 建议先在测试网上测试，确认无误后再使用主网。

## 故障排除

### 问题1: 导入错误

```
ImportError: Extended交易所模块未找到
```

**解决方案**: 确保 `jiaoyisuoshili/extended.py` 文件存在，并且Extended SDK已安装。

### 问题2: 初始化失败

```
RuntimeError: 客户端未初始化
```

**解决方案**: 检查所有必需参数（api_key, private_key, public_key, vault）是否正确配置。

### 问题3: 交易对格式错误

```
ValueError: 未找到市场: BTC/USDT
```

**解决方案**: Extended使用 `BTC-USD` 格式，系统会自动转换，但请确保交易对在Extended上存在。

## 技术细节

### 异步/同步适配

Extended SDK使用异步接口，但我们的BaseExchange接口是同步的。`ExtendedExchange`类通过以下方式适配：

1. 使用 `asyncio.run()` 或线程池执行异步操作
2. 检测当前线程是否有事件循环
3. 如果没有事件循环，创建新的事件循环
4. 如果有事件循环，使用线程池避免冲突

### 数据格式转换

Extended返回的数据格式与标准格式略有不同，`ExtendedExchange`会自动转换：

- 订单方向: `BUY/SELL` → `buy/sell`
- 订单类型: `LIMIT/MARKET` → `limit/market`
- 订单状态: `NEW/FILLED/CANCELLED` → 保持原样

## 更新日志

- **v1.0.0**: 初始版本，支持基本的交易功能

