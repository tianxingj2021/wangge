#!/bin/bash
# 网格交易系统快速部署脚本

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then 
    print_error "请不要使用 root 用户运行此脚本"
    print_info "建议创建专用用户: sudo useradd -m -s /bin/bash wangge"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

print_info "开始部署网格交易系统..."
print_info "项目目录: $SCRIPT_DIR"

# 1. 检查 Python
print_info "检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    print_error "未找到 python3，请先安装 Python 3.9+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_info "Python 版本: $(python3 --version)"

# 2. 创建虚拟环境
print_info "创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_info "虚拟环境创建成功"
else
    print_warn "虚拟环境已存在，跳过创建"
fi

# 3. 激活虚拟环境
print_info "激活虚拟环境..."
source venv/bin/activate

# 4. 升级 pip
print_info "升级 pip..."
pip install --upgrade pip --quiet

# 5. 安装依赖
print_info "安装项目依赖..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_info "依赖安装完成"
else
    print_error "未找到 requirements.txt 文件"
    exit 1
fi

# 6. 检查 Extended SDK（可选）
read -p "是否使用 Extended 交易所？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "安装 Extended SDK..."
    pip install x10-python-trading-starknet || print_warn "Extended SDK 安装失败，请手动安装"
fi

# 7. 检查 .env 文件
print_info "检查配置文件..."
if [ ! -f ".env" ]; then
    print_warn ".env 文件不存在"
    if [ -f ".env.example" ]; then
        print_info "从 .env.example 创建 .env 文件..."
        cp .env.example .env
        print_warn "请编辑 .env 文件，填入你的 API 密钥"
    else
        print_warn "请手动创建 .env 文件并配置交易所信息"
    fi
else
    print_info ".env 文件已存在"
fi

# 8. 设置文件权限
print_info "设置文件权限..."
chmod 600 .env 2>/dev/null || print_warn "无法设置 .env 权限"
chmod +x run.py 2>/dev/null || print_warn "无法设置 run.py 权限"

# 9. 创建日志目录
print_info "创建日志目录..."
mkdir -p logs
chmod 755 logs

# 10. 测试导入
print_info "测试依赖导入..."
python3 -c "
import sys
try:
    import fastapi
    import uvicorn
    print('✓ 核心依赖导入成功')
except ImportError as e:
    print(f'✗ 依赖导入失败: {e}')
    sys.exit(1)
" || exit 1

# 11. 生成 systemd 服务文件（可选）
print_info "部署完成！"
echo
print_info "下一步操作："
echo "1. 编辑 .env 文件，配置交易所 API 密钥"
echo "2. 测试启动: source venv/bin/activate && python run.py"
echo "3. 配置 systemd 服务（参考 DEPLOYMENT.md）"
echo
print_info "查看详细部署文档: cat DEPLOYMENT.md"

