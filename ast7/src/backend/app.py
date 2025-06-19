"""
2D/3D AST可视化编辑器 - 主应用
"""

import os
from flask import Flask, render_template
from flask_cors import CORS
from ..api.controllers import api_bp


def create_app():
    """应用工厂函数"""
    # 获取src目录的绝对路径
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(src_dir, "templates")
    static_dir = os.path.join(src_dir, "static")

    app = Flask(__name__, static_folder=static_dir, template_folder=template_dir)

    # 启用CORS
    CORS(app)

    # 注册蓝图
    app.register_blueprint(api_bp)

    # 主页路由
    @app.route("/")
    def index():
        return render_template("index.html")

    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "页面未找到"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "服务器内部错误"}, 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5001, debug=True)
