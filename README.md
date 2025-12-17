# 网格交易系统

一个模块化的网格交易系统，支持多交易所，采用前后端分离架构。

## 项目结构

```
wangge/
├── exchanges/          # 交易所接口模块
│   ├── __init__.py
│   ├── base.py        # 交易所抽象基类
│   ├── binance.py     # 币安交易所实现
│   └── factory.py     # 交易所工厂
├── strategies/         # 交易策略模块
│   ├── __init__.py
│   ├── base.py        # 策略基类
│   └── grid.py        # 网格交易策略
├── core/              # 核心功能模块
│   ├── __init__.py
│   ├── order_manager.py    # 订单管理
│   ├── account_manager.py  # 账户管理
│   └── position_manager.py # 持仓管理
├── backend/           # 后端API服务
│   ├── __init__.py
│   ├── main.py       # FastAPI主应用
│   ├── api/          # API路由
│   │   ├── __init__.py
│   │   ├── exchange.py
│   │   ├── strategy.py
│   │   └── order.py
│   └── models/       # 数据模型
│       ├── __init__.py
│       └── schemas.py
├── frontend/         # 前端界面
│   ├── static/       # 静态文件
│   └── templates/    # HTML模板
├── utils/            # 工具函数
│   ├── __init__.py
│   ├── logger.py     # 日志配置
│   └── helpers.py    # 辅助函数
├── config/           # 配置文件
│   ├── __init__.py
│   └── settings.py   # 配置管理
├── tests/            # 测试文件
│   ├── __init__.py
│   ├── test_exchanges.py
│   └── test_strategies.py
├── requirements.txt  # 依赖包
└── README.md         # 项目说明
```

## 功能特性

- ✅ 模块化设计，易于扩展
- ✅ 支持多交易所（Binance、Extended等）
- ✅ 前后端分离架构
- ✅ 网格交易策略
- ✅ RESTful API接口
- ✅ 订单和账户管理
- ✅ 异步/同步接口适配

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# 交易所API配置
EXCHANGE_API_KEY=your_api_key
EXCHANGE_SECRET_KEY=your_secret_key
EXCHANGE_NAME=binance

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
```

### 3. 启动后端服务

```bash
python -m backend.main
```

### 4. 访问前端界面

打开浏览器访问：`http://localhost:8000`

## 支持的交易所

### Binance（币安）

标准配置，使用API Key和Secret Key。

### Extended

基于StarkNet的永续合约交易所，需要额外配置：

```env
EXCHANGE_NAME=extended
EXCHANGE_API_KEY=your_api_key
EXCHANGE_SECRET_KEY=your_private_key
EXCHANGE_PUBLIC_KEY=your_public_key
EXCHANGE_VAULT=your_vault_id
EXCHANGE_TESTNET=true
```

详细配置说明请参考 [EXTENDED_SETUP.md](EXTENDED_SETUP.md)

## 添加新交易所

1. 在 `exchanges/` 目录下创建新的交易所实现文件
2. 继承 `BaseExchange` 类并实现所有抽象方法
3. 在文件末尾注册新交易所

示例：

```python
# exchanges/okx.py
from exchanges.base import BaseExchange
from exchanges.factory import ExchangeFactory

class OKXExchange(BaseExchange):
    def __init__(self, api_key: str, secret_key: str, **kwargs):
        super().__init__(api_key, secret_key, **kwargs)
        # 初始化OKX API客户端
    
    def get_balance(self, currency=None):
        # 实现获取余额
        pass
    
    def place_order(self, symbol, side, order_type, quantity, price=None, **kwargs):
        # 实现下单
        pass
    
    # ... 实现其他必需方法

# 注册交易所
ExchangeFactory.register('okx', OKXExchange)
```

然后在配置文件中使用新交易所：

```env
EXCHANGE_NAME=okx
```

## 开发指南

详见各模块的文档注释。

