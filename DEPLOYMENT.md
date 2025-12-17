# 服务器部署指南

本指南将帮助你将网格交易系统部署到 Linux 服务器上。

## 目录

1. [服务器环境准备](#1-服务器环境准备)
2. [代码部署](#2-代码部署)
3. [依赖安装](#3-依赖安装)
4. [配置文件设置](#4-配置文件设置)
5. [使用 Systemd 管理服务](#5-使用-systemd-管理服务)
6. [Nginx 反向代理（可选）](#6-nginx-反向代理可选)
7. [日志管理](#7-日志管理)
8. [监控和维护](#8-监控和维护)
9. [故障排查](#9-故障排查)

---

## 1. 服务器环境准备

### 1.1 系统要求

- **操作系统**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / 其他 Linux 发行版
- **Python**: 3.9+ (推荐 3.10 或 3.11)
- **内存**: 至少 2GB RAM
- **磁盘**: 至少 10GB 可用空间
- **网络**: 稳定的网络连接（用于连接交易所 API）

### 1.2 更新系统

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 1.3 安装 Python 和必要工具

```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv git curl wget

# CentOS/RHEL
sudo yum install -y python3 python3-pip git curl wget
```

### 1.4 使用 root 用户

本部署指南使用 root 用户进行部署。如果服务器已配置 root 用户，直接使用即可。

**重要说明**：
- 确保你已以 root 用户登录，或使用 `sudo su -` 切换到 root 用户
- 如果使用 root 用户，执行命令时不需要加 `sudo` 前缀
- 项目将部署在 `/root/wangge` 目录

---

## 2. 代码部署

### 2.1 克隆或上传代码

**方式1：使用 Git（推荐）**

```bash
cd ~
git clone https://github.com/tianxingj2021/wangge.git wangge
cd wangge
```

**方式2：使用 SCP 上传**

在本地机器上执行：

```bash
scp -r /path/to/wangge root@server:/root/
```

然后在服务器上：

```bash
cd /root/wangge
```

### 2.2 设置项目目录权限

```bash
# 确保 root 用户拥有项目目录
chown -R root:root /root/wangge
chmod -R 755 /root/wangge
```

---

## 3. 依赖安装

### 3.1 创建虚拟环境

```bash
cd /root/wangge
python3 -m venv venv
```

### 3.2 激活虚拟环境

```bash
source venv/bin/activate
```

### 3.3 升级 pip

```bash
pip install --upgrade pip
```

### 3.4 安装项目依赖

```bash
pip install -r requirements.txt
```

### 3.5 安装 Extended SDK（如果使用 Extended 交易所）

```bash
pip install x10-python-trading-starknet
```

### 3.6 验证安装

```bash
python -c "import fastapi, uvicorn; print('依赖安装成功')"
```

---

## 4. 配置文件设置

### 4.1 创建 .env 文件（服务器运行配置）

**重要说明**：交易所 API 密钥是通过前端界面配置的，不需要在 `.env` 文件中配置。`.env` 文件仅用于服务器运行配置。

```bash
cd /root/wangge
cp .env.example .env  # 如果有示例文件
# 或者直接创建
nano .env
```

### 4.2 配置 .env 文件（仅服务器配置）

`.env` 文件只需要配置服务器运行参数，**不需要配置交易所 API 密钥**：

```env
# 服务器配置（必填）
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

**说明**：
- `API_HOST`: 服务监听地址，通常为 `0.0.0.0`（允许外部访问）
- `API_PORT`: 服务端口，默认 `8000`
- `DEBUG`: 生产环境设置为 `false`
- `LOG_LEVEL`: 日志级别，推荐 `INFO`

### 4.3 设置文件权限

```bash
chmod 600 .env
```

### 4.4 配置交易所信息（通过前端界面）

**交易所配置不需要手动创建文件**，系统会在首次通过前端界面配置时自动创建 `config/exchange_config.json`。

**配置步骤**：
1. 启动服务后，访问前端界面
2. 进入"配置"页面
3. 填写交易所信息（API 密钥、私钥等）
4. 点击"保存配置"

系统会自动将配置保存到 `config/exchange_config.json` 文件中。

**注意**：如果服务器上已有 `config/exchange_config.json` 文件，请确保：
- 文件权限正确：`chmod 644 config/exchange_config.json`
- 文件格式正确（JSON 格式）
- 包含有效的 API 密钥信息

---

## 5. 使用 Systemd 管理服务

### 5.1 创建 Systemd 服务文件

```bash
nano /etc/systemd/system/wangge.service
```

**注意**：使用 root 用户时，不需要 `sudo` 前缀。

### 5.2 服务文件内容

```ini
[Unit]
Description=网格交易系统
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/root/wangge
Environment="PATH=/root/wangge/venv/bin"
ExecStart=/root/wangge/venv/bin/python /root/wangge/run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 日志路径
ReadWritePaths=/root/wangge/logs

[Install]
WantedBy=multi-user.target
```

**注意**：如果项目部署在其他路径，请修改 `WorkingDirectory` 和 `ExecStart` 中的路径。

### 5.3 重载 Systemd 配置

```bash
systemctl daemon-reload
```

### 5.4 启动服务

```bash
systemctl start wangge
```

### 5.5 设置开机自启

```bash
systemctl enable wangge
```

### 5.6 检查服务状态

```bash
# 查看服务状态
systemctl status wangge

# 查看日志
journalctl -u wangge -f

# 查看最近100行日志
journalctl -u wangge -n 100
```

### 5.7 常用服务管理命令

```bash
# 启动服务
systemctl start wangge

# 停止服务
systemctl stop wangge

# 重启服务
systemctl restart wangge

# 查看服务状态
systemctl status wangge

# 禁用开机自启
systemctl disable wangge

# 启用开机自启
systemctl enable wangge
```

---

## 6. Nginx 反向代理（可选）

如果需要通过域名访问，或需要 HTTPS，可以配置 Nginx 反向代理。

### 6.1 安装 Nginx

```bash
# Ubuntu/Debian
sudo apt install -y nginx

# CentOS/RHEL
sudo yum install -y nginx
```

### 6.2 创建 Nginx 配置文件

```bash
nano /etc/nginx/sites-available/wangge
```

**HTTP 配置（开发/测试）：**

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或 IP

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

**HTTPS 配置（生产环境，使用 Let's Encrypt）：**

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 6.3 启用配置

```bash
# 创建符号链接（Ubuntu/Debian）
ln -s /etc/nginx/sites-available/wangge /etc/nginx/sites-enabled/

# 或者直接复制到 sites-enabled（CentOS）
cp /etc/nginx/sites-available/wangge /etc/nginx/conf.d/wangge.conf

# 测试配置
nginx -t

# 重启 Nginx
systemctl restart nginx
```

### 6.4 配置防火墙

```bash
# Ubuntu/Debian (UFW)
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# CentOS/RHEL (firewalld)
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

### 6.5 使用 Let's Encrypt 获取 SSL 证书（HTTPS）

```bash
# 安装 Certbot
apt install -y certbot python3-certbot-nginx  # Ubuntu/Debian
yum install -y certbot python3-certbot-nginx  # CentOS/RHEL

# 获取证书
certbot --nginx -d your-domain.com

# 自动续期测试
certbot renew --dry-run
```

---

## 7. 日志管理

### 7.1 查看应用日志

应用日志保存在 `/root/wangge/logs/` 目录：

```bash
# 查看最新日志
tail -f /root/wangge/logs/app_$(date +%Y-%m-%d).log

# 查看所有日志
ls -lh /root/wangge/logs/

# 搜索错误
grep -i error /root/wangge/logs/*.log
```

### 7.2 查看 Systemd 日志

```bash
# 实时查看日志
journalctl -u wangge -f

# 查看最近100行
journalctl -u wangge -n 100

# 查看今天的日志
journalctl -u wangge --since today

# 查看特定时间段的日志
journalctl -u wangge --since "2024-01-01 00:00:00" --until "2024-01-01 23:59:59"
```

### 7.3 日志轮转（可选）

创建日志轮转配置：

```bash
nano /etc/logrotate.d/wangge
```

内容：

```
/root/wangge/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
    sharedscripts
}
```

---

## 8. 监控和维护

### 8.1 健康检查

```bash
# 检查服务是否运行
curl http://localhost:8000/health

# 或通过 Nginx
curl http://your-domain.com/health
```

### 8.2 监控脚本示例

创建一个简单的监控脚本：

```bash
nano /root/monitor_wangge.sh
```

内容：

```bash
#!/bin/bash
SERVICE="wangge"
URL="http://localhost:8000/health"

if systemctl is-active --quiet $SERVICE; then
    echo "$(date): Service $SERVICE is running"
    
    # 检查健康状态
    if curl -f -s $URL > /dev/null; then
        echo "$(date): Health check passed"
    else
        echo "$(date): Health check failed, restarting service"
        systemctl restart $SERVICE
    fi
else
    echo "$(date): Service $SERVICE is not running, starting..."
    systemctl start $SERVICE
fi
```

设置执行权限：

```bash
chmod +x /root/monitor_wangge.sh
```

添加到 crontab（每5分钟检查一次）：

```bash
crontab -e
```

添加：

```
*/5 * * * * /root/monitor_wangge.sh >> /root/monitor.log 2>&1
```

### 8.3 资源监控

```bash
# 查看进程资源使用
ps aux | grep wangge

# 查看内存使用
free -h

# 查看磁盘使用
df -h

# 查看网络连接
netstat -tulpn | grep 8000
# 或使用 ss 命令
ss -tulpn | grep 8000
```

---

## 9. 故障排查

### 9.1 服务无法启动

```bash
# 检查服务状态
systemctl status wangge

# 查看详细错误日志
journalctl -u wangge -n 50 --no-pager

# 检查配置文件
cd /root/wangge
source venv/bin/activate
python -c "from config.settings import get_settings; print(get_settings())"

# 手动测试启动
python run.py
```

### 9.2 端口被占用

```bash
# 检查端口占用
netstat -tulpn | grep 8000
# 或
lsof -i :8000
# 或使用 ss 命令
ss -tulpn | grep 8000

# 修改端口（在 .env 文件中）
API_PORT=8001
```

### 9.3 依赖问题

```bash
# 重新安装依赖
cd /root/wangge
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### 9.4 权限问题

```bash
# 检查文件权限
ls -la /root/wangge

# 修复权限（root 用户通常不需要）
chown -R root:root /root/wangge
chmod 600 /root/wangge/.env
```

### 9.5 网络连接问题

```bash
# 测试交易所 API 连接
curl https://api.binance.com/api/v3/ping

# 检查防火墙
ufw status  # Ubuntu/Debian
firewall-cmd --list-all  # CentOS/RHEL
```

### 9.6 查看实时日志

```bash
# 同时查看 systemd 日志和应用日志
journalctl -u wangge -f &
tail -f /root/wangge/logs/app_$(date +%Y-%m-%d).log
```

---

## 10. 更新部署

### 10.1 更新代码

```bash
cd /root/wangge

# 如果使用 Git
git pull origin main

# 或重新上传文件
# scp -r /path/to/wangge root@server:/root/
```

**注意**：如果仓库地址是 `https://github.com/tianxingj2021/wangge.git`，确保远程仓库已正确配置：

```bash
# 检查远程仓库地址
git remote -v

# 如果地址不正确，更新为：
git remote set-url origin https://github.com/tianxingj2021/wangge.git
```

### 10.2 更新依赖

```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### 10.3 重启服务

```bash
systemctl restart wangge
systemctl status wangge
```

---

## 11. 安全建议

1. **保护 .env 文件**：设置 `chmod 600 .env`
2. **使用 HTTPS**：在生产环境配置 SSL 证书
3. **配置防火墙**：只开放必要的端口
4. **定期更新**：保持系统和依赖包更新
5. **备份配置**：定期备份 `.env` 和 `exchange_config.json`
6. **监控日志**：定期检查日志，发现异常及时处理
7. **限制访问**：如果可能，使用防火墙限制 API 访问来源

---

## 12. 快速部署脚本

可以创建一个自动化部署脚本：

```bash
nano /root/deploy_wangge.sh
```

内容：

```bash
#!/bin/bash
set -e

echo "开始部署网格交易系统..."

# 1. 创建虚拟环境
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 升级 pip
pip install --upgrade pip

# 4. 安装依赖
pip install -r requirements.txt

# 5. 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "警告: .env 文件不存在，请创建并配置"
    exit 1
fi

# 6. 设置权限
chmod 600 .env

echo "部署完成！"
echo "请确保已配置 .env 文件，然后运行: systemctl start wangge"
```

设置执行权限：

```bash
chmod +x /root/deploy_wangge.sh
```

---

## 总结

部署完成后，你的系统应该：

1. ✅ 通过 systemd 自动管理
2. ✅ 开机自动启动
3. ✅ 自动重启（如果崩溃）
4. ✅ 日志记录完整
5. ✅ 可通过域名访问（如果配置了 Nginx）

**访问地址**：
- 直接访问：`http://your-server-ip:8000`
- 通过 Nginx：`http://your-domain.com` 或 `https://your-domain.com`

**下一步**：
1. 配置交易所 API 密钥
2. 启动服务
3. 访问前端界面测试功能
4. 设置监控和告警

祝部署顺利！🎉

