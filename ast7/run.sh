#!/bin/bash

# 可视化 AST 编辑器启动脚本

echo "🌳 启动可视化 AST 编辑器..."
echo "================================"

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 Python 3，请先安装 Python 3"
    exit 1
fi

# 虚拟环境目录
VENV_DIR=".venv"

# 创建虚拟环境（如果不存在）
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 创建 Python 虚拟环境..."
    python3 -m venv $VENV_DIR
    
    if [ $? -ne 0 ]; then
        echo "❌ 虚拟环境创建失败"
        exit 1
    fi
    
    echo "✅ 虚拟环境创建成功"
else
    echo "📁 找到现有虚拟环境"
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source $VENV_DIR/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ 虚拟环境激活失败"
    exit 1
fi

echo "✅ 虚拟环境已激活"

# 升级 pip
echo "⬆️ 升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "📦 安装项目依赖..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败，请检查网络连接"
    exit 1
fi

echo "✅ 依赖安装完成"
echo ""

# 启动服务器
echo "🚀 启动 Flask 服务器..."
echo "服务器地址: http://127.0.0.1:5001"
echo "按 Ctrl+C 停止服务器"
echo ""
echo "💡 提示：服务器停止后，虚拟环境会自动退出"
echo ""

python app.py 