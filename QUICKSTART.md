# 快速启动指南

## 环境设置完成 ✅

虚拟环境已创建，所有依赖已安装成功！

## 激活虚拟环境

每次使用项目前，需要激活虚拟环境：

```bash
source venv/bin/activate
```

激活后，命令行提示符前会显示 `(venv)`。

## 退出虚拟环境

```bash
deactivate
```

## 启动服务

### 方式1：使用启动脚本

```bash
source venv/bin/activate
python run.py
```

### 方式2：直接使用uvicorn

```bash
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## 访问系统

启动成功后，可以通过以下地址访问：

- **前端界面**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 配置环境变量

在启动服务前，请确保已创建 `.env` 文件并配置了交易所信息：

```bash
cp .env.example .env
# 然后编辑 .env 文件，填入你的API密钥
```

### Binance配置示例

```env
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=your_api_key
EXCHANGE_SECRET_KEY=your_secret_key
EXCHANGE_TESTNET=true
```

### Extended配置示例

```env
EXCHANGE_NAME=extended
EXCHANGE_API_KEY=your_api_key
EXCHANGE_SECRET_KEY=your_private_key
EXCHANGE_PUBLIC_KEY=your_public_key
EXCHANGE_VAULT=12345
EXCHANGE_TESTNET=true
```

## 安装Extended SDK（可选）

如果使用Extended交易所，需要额外安装SDK：

```bash
source venv/bin/activate
pip install x10-python-trading-starknet
```

## 常见问题

### 1. 虚拟环境未激活

如果看到 `ModuleNotFoundError`，请确保已激活虚拟环境：

```bash
source venv/bin/activate
```

### 2. 端口被占用

如果8000端口被占用，可以修改端口：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

或在 `.env` 文件中设置：

```env
API_PORT=8001
```

### 3. 依赖缺失

如果缺少依赖，重新安装：

```bash
source venv/bin/activate
pip install -r requirements.txt
```

## 下一步

1. 配置 `.env` 文件
2. 启动服务
3. 访问 http://localhost:8000 查看前端界面
4. 访问 http://localhost:8000/docs 查看API文档

祝使用愉快！🎉

