#!/bin/bash

# 停止可视化 AST 编辑器服务器

echo "🛑 停止可视化 AST 编辑器服务器..."

# 查找并停止 Python 服务器进程
if pgrep -f "python.*app.py" > /dev/null; then
    echo "📍 找到运行中的服务器进程"
    pkill -f "python.*app.py"
    
    # 等待进程完全停止
    sleep 2
    
    # 检查是否成功停止
    if ! pgrep -f "python.*app.py" > /dev/null; then
        echo "✅ 服务器已成功停止"
    else
        echo "⚠️ 强制终止进程..."
        pkill -9 -f "python.*app.py"
        echo "✅ 服务器已强制停止"
    fi
else
    echo "ℹ️ 没有找到运行中的服务器进程"
fi

echo "👋 再见！" 