# 架构设计文档

## 系统架构

### 整体架构

```
┌─────────────┐
│   Frontend  │  (HTML/CSS/JavaScript)
│   (Web UI)  │
└──────┬──────┘
       │ HTTP/REST
┌──────▼──────┐
│   Backend   │  (FastAPI)
│   (API)     │
└──────┬──────┘
       │
┌──────▼──────────────────┐
│   Strategy Layer         │
│   (Grid Strategy)        │
└──────┬───────────────────┘
       │
┌──────▼──────────────────┐
│   Core Layer             │
│   (Order/Account/Position│
│    Managers)             │
└──────┬───────────────────┘
       │
┌──────▼──────────────────┐
│   Exchange Layer         │
│   (BaseExchange)         │
└──────┬───────────────────┘
       │
┌──────▼──────────────────┐
│   Exchange APIs          │
│   (Binance/OKX/...)     │
└──────────────────────────┘
```

## 模块说明

### 1. 交易所层 (exchanges/)

**职责**: 提供统一的交易所接口抽象

- `base.py`: 定义 `BaseExchange` 抽象基类，所有交易所必须实现
- `factory.py`: 交易所工厂，用于创建和管理交易所实例
- `binance.py`: 币安交易所实现（示例）

**设计模式**: 
- 策略模式：不同交易所实现统一接口
- 工厂模式：通过工厂创建交易所实例

### 2. 核心层 (core/)

**职责**: 提供核心业务功能

- `order_manager.py`: 订单管理，包括下单、取消、查询
- `account_manager.py`: 账户管理，余额查询和管理
- `position_manager.py`: 持仓管理

**特点**:
- 独立于具体交易所实现
- 提供统一的业务逻辑接口

### 3. 策略层 (strategies/)

**职责**: 实现各种交易策略

- `base.py`: 策略基类，定义策略接口
- `grid.py`: 网格交易策略实现

**网格策略原理**:
1. 在价格区间内设置多个价格层级
2. 在每个层级设置买卖订单
3. 订单成交后自动补充新订单
4. 实现低买高卖的自动化交易

### 4. 后端层 (backend/)

**职责**: 提供RESTful API服务

- `main.py`: FastAPI主应用
- `api/`: API路由模块
  - `exchange.py`: 交易所相关API
  - `order.py`: 订单相关API
  - `strategy.py`: 策略相关API
- `models/`: 数据模型（Pydantic Schemas）

**API设计**:
- RESTful风格
- 使用Pydantic进行数据验证
- 依赖注入管理资源

### 5. 前端层 (frontend/)

**职责**: 提供Web用户界面

- `templates/`: HTML模板
- `static/`: 静态资源
  - `css/`: 样式文件
  - `js/`: JavaScript文件

**特点**:
- 单页应用（SPA）
- 通过RESTful API与后端通信
- 响应式设计

## 数据流

### 启动网格策略流程

```
用户提交策略配置
    ↓
前端发送 POST /api/v1/strategy/grid/start
    ↓
后端创建 GridStrategy 实例
    ↓
策略调用 OrderManager.place_order()
    ↓
OrderManager 调用 Exchange.place_order()
    ↓
交易所API执行下单
    ↓
返回订单结果
    ↓
策略保存订单信息
    ↓
返回策略ID给前端
```

### 策略更新流程

```
定时任务/手动触发更新
    ↓
调用 Strategy.update()
    ↓
检查未成交订单状态
    ↓
发现订单已成交
    ↓
根据成交订单补充新订单
    ↓
保持网格完整性
```

## 扩展性设计

### 添加新交易所

1. 继承 `BaseExchange`
2. 实现所有抽象方法
3. 注册到 `ExchangeFactory`
4. 无需修改其他代码

### 添加新策略

1. 继承 `BaseStrategy`
2. 实现策略逻辑
3. 添加对应的API路由（可选）
4. 前端添加策略配置界面（可选）

### 添加新功能

- 数据库持久化：在 `core/` 层添加数据访问层
- 消息队列：用于异步任务处理
- WebSocket：用于实时数据推送

## 安全考虑

1. **API密钥管理**: 使用环境变量，不提交到代码库
2. **输入验证**: 使用Pydantic进行数据验证
3. **错误处理**: 统一的异常处理机制
4. **日志记录**: 记录所有重要操作

## 性能优化

1. **缓存**: 订单和余额信息本地缓存
2. **异步**: 使用FastAPI的异步特性
3. **连接池**: HTTP客户端使用连接池
4. **批量操作**: 支持批量查询和操作

## 测试策略

1. **单元测试**: 测试各个模块的功能
2. **集成测试**: 测试模块间的交互
3. **模拟测试**: 使用模拟数据测试交易所接口

