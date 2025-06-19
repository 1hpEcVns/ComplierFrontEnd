#!/usr/bin/env python3
"""
AST可视化编辑器启动文件
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.backend.app import create_app

if __name__ == "__main__":
    app = create_app()
    print("🌳 2D/3D AST编辑器正在启动...")
    print("访问地址: http://127.0.0.1:5001")
    app.run(host="127.0.0.1", port=5001, debug=True)
