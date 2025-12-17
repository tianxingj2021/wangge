# 上传代码到 GitHub 详细步骤

⚠️ **重要安全提示**：在上传前，请确保所有包含 API 密钥、私钥等敏感信息的文件已被 `.gitignore` 排除！

---

## 第一步：检查敏感文件（重要！）

### 1.1 检查 .gitignore 文件

确保 `.gitignore` 包含以下内容：

```
.env
config/exchange_config.json
logs/
*.log
venv/
```

### 1.2 检查是否有敏感文件已被 Git 跟踪

```bash
# 检查 .env 文件是否被跟踪
git ls-files | grep -E "\.env$|exchange_config\.json"

# 如果看到输出，说明这些文件已被跟踪，需要从 Git 中移除（见第二步）
```

### 1.3 确认敏感文件存在

检查以下文件是否存在且包含真实密钥：
- `.env` - 应该被忽略
- `config/exchange_config.json` - 应该被忽略

**如果这些文件包含真实密钥，它们必须被 `.gitignore` 排除！**

---

## 第二步：清理已跟踪的敏感文件（如果存在）

如果敏感文件已经被 Git 跟踪，需要从 Git 历史中移除：

### 2.1 从 Git 索引中移除（但保留本地文件）

```bash
# 移除 .env（如果已被跟踪）
git rm --cached .env

# 移除 exchange_config.json（如果已被跟踪）
git rm --cached config/exchange_config.json

# 移除日志文件（如果已被跟踪）
git rm --cached -r logs/
```

### 2.2 提交移除操作

```bash
git add .gitignore
git commit -m "Remove sensitive files from Git tracking"
```

### 2.3 如果已经推送到远程（危险！）

如果敏感文件已经被推送到 GitHub，需要：

1. **立即更换所有 API 密钥**（因为密钥已经泄露）
2. 从 Git 历史中完全移除（使用 `git filter-branch` 或 `BFG Repo-Cleaner`）

**注意**：如果已经推送到 GitHub，建议创建新的仓库，不要使用旧的。

---

## 第三步：创建示例配置文件

### 3.1 创建 .env.example

```bash
# 如果还没有，创建一个示例文件
cat > .env.example << 'EOF'
# 交易所配置
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=your_api_key_here
EXCHANGE_SECRET_KEY=your_secret_key_here
EXCHANGE_TESTNET=true

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
EOF
```

### 3.2 创建 exchange_config.json.example

```bash
# 创建示例配置文件
cat > config/exchange_config.json.example << 'EOF'
{
  "extended_account": {
    "name": "Extended测试账号",
    "account_key": "extended_account",
    "exchange": "extended",
    "api_key": "your_api_key_here",
    "secret_key": "your_private_key_here",
    "testnet": true,
    "public_key": "your_public_key_here",
    "private_key": "your_private_key_here",
    "vault": 12345,
    "default_market": "BTC-USD"
  }
}
EOF
```

---

## 第四步：初始化 Git 仓库（如果还没有）

### 4.1 检查是否已有 Git 仓库

```bash
cd /Volumes/Lenovo/python/wangge
ls -la .git
```

如果看到 `.git` 目录，说明已有仓库，跳到第五步。

### 4.2 初始化 Git 仓库

```bash
git init
```

### 4.3 配置 Git 用户信息（如果还没配置）

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

---

## 第五步：添加文件到 Git

### 5.1 检查要添加的文件

```bash
# 查看哪些文件会被添加（不包括 .gitignore 中的文件）
git status
```

**确认以下文件不会被添加**：
- `.env`
- `config/exchange_config.json`
- `logs/` 目录
- `venv/` 目录

### 5.2 添加所有文件

```bash
git add .
```

### 5.3 再次检查（重要！）

```bash
# 查看将要提交的文件
git status

# 特别检查是否有敏感文件
git diff --cached --name-only | grep -E "\.env$|exchange_config\.json"
```

**如果看到 `.env` 或 `exchange_config.json`，立即停止！** 检查 `.gitignore` 是否正确。

### 5.4 提交文件

```bash
git commit -m "Initial commit: 网格交易系统"
```

---

## 第六步：在 GitHub 创建仓库

### 6.1 登录 GitHub

访问 https://github.com 并登录

### 6.2 创建新仓库

1. 点击右上角的 **"+"** → **"New repository"**
2. 填写仓库信息：
   - **Repository name**: `wangge`（或你喜欢的名字）
   - **Description**: `网格交易系统`
   - **Visibility**: 
     - `Public` - 公开（代码可见，但敏感文件已排除）
     - `Private` - 私有（推荐，更安全）
3. **不要**勾选 "Initialize this repository with a README"（因为本地已有代码）
4. 点击 **"Create repository"**

### 6.3 获取仓库 URL

创建后，GitHub 会显示仓库 URL，类似：
- HTTPS: `https://github.com/your-username/wangge.git`
- SSH: `git@github.com:your-username/wangge.git`

**🔧 记住这个 URL，下一步会用到**

---

## 第七步：连接本地仓库到 GitHub

### 7.1 添加远程仓库

```bash
# 使用 HTTPS（推荐新手）
git remote add origin https://github.com/your-username/wangge.git

# 或使用 SSH（如果已配置 SSH 密钥）
# git remote add origin git@github.com:your-username/wangge.git
```

**🔧 替换 `your-username` 和 `wangge` 为你的实际值**

### 7.2 验证远程仓库

```bash
git remote -v
```

应该显示：
```
origin  https://github.com/your-username/wangge.git (fetch)
origin  https://github.com/your-username/wangge.git (push)
```

---

## 第八步：推送代码到 GitHub

### 8.1 推送代码

```bash
# 首次推送
git push -u origin main

# 如果默认分支是 master，使用：
# git push -u origin master
```

### 8.2 如果遇到认证问题

**HTTPS 方式**：
- GitHub 现在要求使用 Personal Access Token（不再支持密码）
- 创建 Token：GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- 权限选择：`repo`
- 推送时，用户名输入你的 GitHub 用户名，密码输入 Token

**SSH 方式**（推荐）：
```bash
# 1. 生成 SSH 密钥（如果还没有）
ssh-keygen -t ed25519 -C "your.email@example.com"

# 2. 复制公钥
cat ~/.ssh/id_ed25519.pub

# 3. 添加到 GitHub：Settings → SSH and GPG keys → New SSH key

# 4. 使用 SSH URL 添加远程仓库
git remote set-url origin git@github.com:your-username/wangge.git

# 5. 再次推送
git push -u origin main
```

### 8.3 推送成功

如果看到类似以下输出，说明成功：

```
Enumerating objects: 123, done.
Counting objects: 100% (123/123), done.
Delta compression using up to 8 threads
Compressing objects: 100% (100/100), done.
Writing objects: 100% (123/123), 50.23 KiB | 5.00 MiB/s, done.
Total 123 (delta 20), reused 0 (delta 0), pack-reused 0
To https://github.com/your-username/wangge.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

---

## 第九步：验证上传结果

### 9.1 在 GitHub 上检查

1. 访问你的仓库：`https://github.com/your-username/wangge`
2. 检查文件列表
3. **确认以下文件不存在**：
   - ❌ `.env`
   - ❌ `config/exchange_config.json`
   - ❌ `logs/` 目录
   - ❌ `venv/` 目录

4. **确认以下文件存在**：
   - ✅ `.env.example`
   - ✅ `config/exchange_config.json.example`
   - ✅ `.gitignore`
   - ✅ `requirements.txt`
   - ✅ `run.py`

### 9.2 检查 .gitignore 是否生效

在 GitHub 仓库页面，点击 "Add file" → "Create new file"，尝试创建 `.env` 文件。

如果 GitHub 提示文件被忽略，说明 `.gitignore` 正常工作。

---

## 第十步：在服务器上克隆代码

### 10.1 SSH 登录服务器

```bash
ssh your_username@your_server_ip
```

### 10.2 克隆仓库

```bash
cd ~
git clone https://github.com/your-username/wangge.git
# 或使用 SSH
# git clone git@github.com:your-username/wangge.git
cd wangge
```

### 10.3 创建配置文件

```bash
# 从示例文件创建 .env
cp .env.example .env
nano .env  # 填入真实的 API 密钥

# 从示例文件创建 exchange_config.json
cp config/exchange_config.json.example config/exchange_config.json
nano config/exchange_config.json  # 填入真实的配置
```

### 10.4 设置权限

```bash
chmod 600 .env
chmod 600 config/exchange_config.json
```

### 10.5 继续部署

按照 `MANUAL_DEPLOYMENT.md` 的步骤继续部署。

---

## 后续更新代码

### 在本地修改代码后

```bash
cd /Volumes/Lenovo/python/wangge

# 1. 查看修改
git status

# 2. 添加修改
git add .

# 3. 提交
git commit -m "描述你的修改"

# 4. 推送到 GitHub
git push
```

### 在服务器上更新代码

```bash
cd ~/wangge

# 1. 停止服务（可选，建议）
sudo systemctl stop wangge

# 2. 拉取最新代码
git pull

# 3. 更新依赖（如果有新依赖）
source venv/bin/activate
pip install -r requirements.txt

# 4. 重启服务
sudo systemctl start wangge
```

---

## 安全检查清单

上传前，确认：

- [ ] `.env` 文件不在 Git 跟踪中
- [ ] `config/exchange_config.json` 不在 Git 跟踪中
- [ ] `logs/` 目录不在 Git 跟踪中
- [ ] `venv/` 目录不在 Git 跟踪中
- [ ] `.gitignore` 文件已正确配置
- [ ] 已创建 `.env.example` 示例文件
- [ ] 已创建 `config/exchange_config.json.example` 示例文件
- [ ] 在 GitHub 上验证敏感文件不存在

---

## 常见问题

### Q1: 推送时提示 "remote: Support for password authentication was removed"

**解决方案**：使用 Personal Access Token 或 SSH 密钥

### Q2: 如何检查敏感文件是否被上传？

```bash
# 在 GitHub 仓库页面搜索文件名
# 或使用 GitHub API
curl https://api.github.com/repos/your-username/wangge/contents/.env
# 如果返回 404，说明文件不存在（安全）
```

### Q3: 如果已经上传了敏感文件怎么办？

1. **立即更换所有 API 密钥**
2. 从 Git 历史中移除文件（复杂，建议创建新仓库）
3. 或使用 `git filter-branch` 清理历史

### Q4: 如何设置私有仓库？

在 GitHub 仓库页面：Settings → Danger Zone → Change visibility → Make private

---

## 总结

✅ **已完成**：
1. 检查并配置 `.gitignore`
2. 创建示例配置文件
3. 初始化 Git 仓库
4. 推送到 GitHub
5. 在服务器上克隆代码

🔒 **安全提示**：
- 永远不要提交包含真实密钥的文件
- 使用私有仓库（如果可能）
- 定期更换 API 密钥
- 使用 GitHub Secrets（如果使用 GitHub Actions）

现在你的代码已经安全地上传到 GitHub 了！🎉

