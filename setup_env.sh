#!/bin/bash
# 虚拟环境设置脚本

set -e

echo "=== 网格交易系统 - 环境设置 ==="
echo ""

# 检查Python版本
echo "1. 检查Python版本..."
python3 --version

# 创建虚拟环境
echo ""
echo "2. 创建虚拟环境..."
if [ -d "venv" ]; then
    echo "虚拟环境已存在，跳过创建"
else
    python3 -m venv venv
    echo "虚拟环境创建成功"
fi

# 激活虚拟环境
echo ""
echo "3. 激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo ""
echo "4. 升级pip..."
pip install --upgrade pip

# 安装依赖
echo ""
echo "5. 安装项目依赖..."
pip install -r requirements.txt

# 检查Extended SDK
echo ""
echo "6. 检查Extended交易所SDK..."
if pip show x10-python-trading-starknet > /dev/null 2>&1; then
    echo "✓ Extended SDK已安装"
else
    echo "⚠ Extended SDK未安装"
    echo "  如果需要使用Extended交易所，请运行: pip install x10-python-trading-starknet"
fi

echo ""
echo "=== 环境设置完成 ==="
echo ""
echo "要激活虚拟环境，请运行:"
echo "  source venv/bin/activate"
echo ""
echo "要退出虚拟环境，请运行:"
echo "  deactivate"

