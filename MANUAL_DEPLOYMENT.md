# 手动部署详细步骤

本指南将逐步指导你完成手动部署，**所有需要修改的地方都会用 🔧 标记**。

---

## 第一步：准备服务器环境

### 1.1 登录服务器

```bash
ssh your_username@your_server_ip
```

### 1.2 更新系统（可选但推荐）

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 1.3 安装必要软件

```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv git curl wget

# CentOS/RHEL
sudo yum install -y python3 python3-pip git curl wget
```

### 1.4 创建专用用户（推荐，更安全）

```bash
# 创建用户
sudo useradd -m -s /bin/bash wangge

# 切换到新用户
sudo su - wangge
```

**🔧 注意**：如果你使用现有用户，请记住你的用户名，后面会用到。

---

## 第二步：上传代码到服务器

### 方式1：使用 SCP（从本地机器执行）

在**本地机器**的终端执行：

```bash
# 替换以下内容：
# - your_username: 你的服务器用户名
# - your_server_ip: 你的服务器IP地址
# - /path/to/wangge: 本地项目路径

scp -r /Volumes/Lenovo/python/wangge your_username@your_server_ip:/home/your_username/
```

### 方式2：使用 Git（如果代码在 Git 仓库）

在**服务器**上执行：

```bash
cd ~
git clone https://github.com/tianxingj2021/wangge.git wangge
cd wangge
```

### 方式3：使用压缩包

在**本地机器**：

```bash
cd /Volumes/Lenovo/python
tar -czf wangge.tar.gz wangge
scp wangge.tar.gz your_username@your_server_ip:/home/your_username/
```

在**服务器**上：

```bash
cd ~
tar -xzf wangge.tar.gz
cd wangge
```

---

## 第三步：设置项目目录

### 3.1 确认项目路径

```bash
# 查看当前路径
pwd

# 应该类似：/home/your_username/wangge
# 🔧 记住这个路径，后面会用到
```

### 3.2 设置权限

```bash
# 确保当前用户拥有项目目录
sudo chown -R $USER:$USER ~/wangge
chmod -R 755 ~/wangge
```

---

## 第四步：创建和配置虚拟环境

### 4.1 创建虚拟环境

```bash
cd ~/wangge
python3 -m venv venv
```

### 4.2 激活虚拟环境

```bash
source venv/bin/activate
```

**提示**：激活后，命令行前面会显示 `(venv)`。

### 4.3 升级 pip

```bash
pip install --upgrade pip
```

### 4.4 安装依赖

```bash
pip install -r requirements.txt
```

### 4.5 安装 Extended SDK（如果使用 Extended 交易所）

```bash
pip install x10-python-trading-starknet
```

### 4.6 验证安装

```bash
python -c "import fastapi, uvicorn; print('依赖安装成功')"
```

---

## 第五步：配置环境变量（重要！）

### 5.1 创建 .env 文件

```bash
cd ~/wangge
nano .env
```

### 5.2 配置内容

**🔧 根据你的交易所选择以下配置之一：**

#### 选项A：Binance 配置

```env
# 交易所配置
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=你的API密钥
EXCHANGE_SECRET_KEY=你的密钥
EXCHANGE_TESTNET=true

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

#### 选项B：Extended 配置

```env
# 交易所配置
EXCHANGE_NAME=extended
EXCHANGE_API_KEY=你的API密钥
EXCHANGE_SECRET_KEY=你的私钥
EXCHANGE_PUBLIC_KEY=你的公钥
EXCHANGE_VAULT=你的Vault ID
EXCHANGE_TESTNET=true

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

**🔧 必须修改的内容**：
- `EXCHANGE_API_KEY`: 替换为你的实际 API 密钥
- `EXCHANGE_SECRET_KEY`: 替换为你的实际密钥
- `EXCHANGE_PUBLIC_KEY`: Extended 需要，替换为你的公钥
- `EXCHANGE_VAULT`: Extended 需要，替换为你的 Vault ID
- `EXCHANGE_TESTNET`: `true` 为测试网，`false` 为主网

保存文件：按 `Ctrl+O`，然后 `Enter`，再按 `Ctrl+X` 退出。

### 5.3 设置文件权限（保护敏感信息）

```bash
chmod 600 .env
```

---

## 第六步：配置交易所信息（如果使用 exchange_config.json）

### 6.1 编辑配置文件

```bash
nano config/exchange_config.json
```

### 6.2 配置内容示例

```json
{
  "binance_account": {
    "name": "Binance测试账号",
    "account_key": "binance_account",
    "exchange": "binance",
    "api_key": "你的API密钥",
    "secret_key": "你的密钥",
    "testnet": true
  },
  "extended_account": {
    "name": "Extended测试账号",
    "account_key": "extended_account",
    "exchange": "extended",
    "api_key": "你的API密钥",
    "private_key": "你的私钥",
    "public_key": "你的公钥",
    "vault": 12345,
    "testnet": true
  }
}
```

**🔧 必须修改的内容**：
- 所有 `你的API密钥`、`你的密钥` 等占位符
- `vault` 的数值（Extended 需要）

保存并退出。

---

## 第七步：测试运行（重要！）

在配置 systemd 之前，先手动测试是否能正常运行。

### 7.1 激活虚拟环境

```bash
cd ~/wangge
source venv/bin/activate
```

### 7.2 手动启动

```bash
python run.py
```

### 7.3 检查输出

你应该看到类似以下输出：

```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 7.4 测试访问

在**另一个终端**（或本地浏览器）测试：

```bash
# 在服务器上测试
curl http://localhost:8000/health

# 应该返回：{"status":"ok","message":"服务运行正常"}
```

### 7.5 停止测试

按 `Ctrl+C` 停止服务。

---

## 第八步：创建 Systemd 服务文件

### 8.1 创建服务文件

```bash
sudo nano /etc/systemd/system/wangge.service
```

### 8.2 服务文件内容

**🔧 复制以下内容，并修改标记的部分**：

```ini
[Unit]
Description=网格交易系统
After=network.target

[Service]
Type=simple
# 🔧 修改1: 改为你的用户名（如果创建了 wangge 用户，就写 wangge）
User=wangge
Group=wangge
# 🔧 修改2: 改为你的实际项目路径（使用 pwd 命令查看）
WorkingDirectory=/home/wangge/wangge
Environment="PATH=/home/wangge/wangge/venv/bin"
# 🔧 修改3: 改为你的实际 Python 路径（通常是项目路径/venv/bin/python）
ExecStart=/home/wangge/wangge/venv/bin/python /home/wangge/wangge/run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
# 🔧 修改4: 改为你的实际日志路径
ReadWritePaths=/home/wangge/wangge/logs

[Install]
WantedBy=multi-user.target
```

**🔧 如何找到需要修改的值**：

1. **用户名和组**：
   ```bash
   whoami  # 查看当前用户名
   ```

2. **项目路径**：
   ```bash
   cd ~/wangge
   pwd  # 显示完整路径，例如：/home/wangge/wangge
   ```

3. **Python 路径**：
   ```bash
   cd ~/wangge
   source venv/bin/activate
   which python  # 显示 Python 路径，例如：/home/wangge/wangge/venv/bin/python
   ```

4. **日志路径**：
   通常是 `项目路径/logs`，例如：`/home/wangge/wangge/logs`

**示例**（如果你的用户名是 `ubuntu`，项目在 `/home/ubuntu/wangge`）：

```ini
[Unit]
Description=网格交易系统
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/wangge
Environment="PATH=/home/ubuntu/wangge/venv/bin"
ExecStart=/home/ubuntu/wangge/venv/bin/python /home/ubuntu/wangge/run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/ubuntu/wangge/logs

[Install]
WantedBy=multi-user.target
```

保存文件：按 `Ctrl+O`，然后 `Enter`，再按 `Ctrl+X` 退出。

---

## 第九步：启动和管理服务

### 9.1 重载 Systemd 配置

```bash
sudo systemctl daemon-reload
```

### 9.2 启动服务

```bash
sudo systemctl start wangge
```

### 9.3 检查服务状态

```bash
sudo systemctl status wangge
```

**正常状态应该显示**：
```
● wangge.service - 网格交易系统
   Loaded: loaded (/etc/systemd/system/wangge.service; enabled)
   Active: active (running) since ...
```

如果显示 `failed`，查看错误信息：

```bash
sudo journalctl -u wangge -n 50 --no-pager
```

### 9.4 设置开机自启

```bash
sudo systemctl enable wangge
```

### 9.5 查看实时日志

```bash
sudo journalctl -u wangge -f
```

按 `Ctrl+C` 退出日志查看。

---

## 第十步：验证部署

### 10.1 测试健康检查

```bash
curl http://localhost:8000/health
```

应该返回：
```json
{"status":"ok","message":"服务运行正常"}
```

### 10.2 测试前端（如果配置了 Nginx 或直接访问）

```bash
# 在服务器上
curl http://localhost:8000

# 或从本地浏览器访问
# http://your_server_ip:8000
```

### 10.3 检查日志

```bash
# 查看应用日志
tail -f ~/wangge/logs/app_$(date +%Y-%m-%d).log

# 查看 systemd 日志
sudo journalctl -u wangge -n 100
```

---

## 第十一步：配置防火墙（如果需要外部访问）

### 11.1 Ubuntu/Debian (UFW)

```bash
# 允许 8000 端口
sudo ufw allow 8000/tcp

# 查看状态
sudo ufw status

# 如果防火墙未启用，启用它
sudo ufw enable
```

### 11.2 CentOS/RHEL (firewalld)

```bash
# 允许 8000 端口
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# 查看状态
sudo firewall-cmd --list-all
```

---

## 常用管理命令

### 服务管理

```bash
# 启动服务
sudo systemctl start wangge

# 停止服务
sudo systemctl stop wangge

# 重启服务
sudo systemctl restart wangge

# 查看状态
sudo systemctl status wangge

# 禁用开机自启
sudo systemctl disable wangge

# 启用开机自启
sudo systemctl enable wangge
```

### 日志查看

```bash
# 实时查看 systemd 日志
sudo journalctl -u wangge -f

# 查看最近 100 行
sudo journalctl -u wangge -n 100

# 查看今天的日志
sudo journalctl -u wangge --since today

# 查看应用日志
tail -f ~/wangge/logs/app_$(date +%Y-%m-%d).log
```

---

## 故障排查

### 问题1：服务无法启动

**检查步骤**：

```bash
# 1. 查看详细错误
sudo journalctl -u wangge -n 50 --no-pager

# 2. 检查服务文件语法
sudo systemctl daemon-reload
sudo systemctl status wangge

# 3. 手动测试运行
cd ~/wangge
source venv/bin/activate
python run.py
```

**常见原因**：
- 路径错误：检查 `WorkingDirectory` 和 `ExecStart` 中的路径
- 权限问题：确保用户有权限访问项目目录
- 依赖缺失：重新安装依赖 `pip install -r requirements.txt`
- 配置文件错误：检查 `.env` 文件格式

### 问题2：端口被占用

```bash
# 检查端口占用
sudo netstat -tulpn | grep 8000

# 或使用 lsof
sudo lsof -i :8000

# 修改端口（在 .env 文件中）
API_PORT=8001
# 然后重启服务
sudo systemctl restart wangge
```

### 问题3：权限问题

```bash
# 检查文件权限
ls -la ~/wangge

# 修复权限
sudo chown -R $USER:$USER ~/wangge
chmod 600 ~/wangge/.env
```

### 问题4：无法访问服务

```bash
# 1. 检查服务是否运行
sudo systemctl status wangge

# 2. 检查防火墙
sudo ufw status  # Ubuntu/Debian
sudo firewall-cmd --list-all  # CentOS/RHEL

# 3. 检查端口监听
sudo netstat -tulpn | grep 8000

# 4. 测试本地访问
curl http://localhost:8000/health
```

---

## 更新部署

当需要更新代码时：

```bash
# 1. 停止服务
sudo systemctl stop wangge

# 2. 更新代码（根据你的方式选择）
# 方式A: Git
cd ~/wangge
git pull origin main

# 如果远程仓库地址不正确，先设置：
# git remote set-url origin https://github.com/tianxingj2021/wangge.git

# 方式B: 重新上传文件
# 在本地执行 scp，然后在服务器上解压

# 3. 更新依赖（如果有新依赖）
source venv/bin/activate
pip install -r requirements.txt

# 4. 重启服务
sudo systemctl start wangge

# 5. 检查状态
sudo systemctl status wangge
```

---

## 总结：需要修改的内容清单

**🔧 必须修改的内容**：

1. ✅ **`.env` 文件**：
   - `EXCHANGE_API_KEY`
   - `EXCHANGE_SECRET_KEY`
   - `EXCHANGE_PUBLIC_KEY`（Extended 需要）
   - `EXCHANGE_VAULT`（Extended 需要）
   - `EXCHANGE_TESTNET`（true/false）

2. ✅ **`config/exchange_config.json`**（如果使用）：
   - API 密钥
   - 私钥/公钥
   - Vault ID

3. ✅ **`/etc/systemd/system/wangge.service`**：
   - `User`：你的用户名
   - `Group`：你的用户组
   - `WorkingDirectory`：项目完整路径
   - `ExecStart`：Python 完整路径和项目路径
   - `ReadWritePaths`：日志目录完整路径

**可选配置**：
- 防火墙端口（如果需要外部访问）
- Nginx 反向代理（如果需要域名访问）

---

## 快速检查清单

部署完成后，检查以下项目：

- [ ] 虚拟环境已创建并激活
- [ ] 所有依赖已安装
- [ ] `.env` 文件已配置并设置权限 600
- [ ] 手动测试运行成功
- [ ] Systemd 服务文件已创建并配置正确路径
- [ ] 服务可以正常启动
- [ ] 健康检查返回正常
- [ ] 日志文件正常生成
- [ ] 开机自启已启用
- [ ] 防火墙已配置（如果需要）

完成以上所有步骤后，你的网格交易系统就已经成功部署到服务器上了！🎉

