"""
应用配置文件
"""

import os


class Config:
    """基础配置"""

    DEBUG = False
    HOST = "127.0.0.1"
    PORT = 5001

    # 安全配置
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

    # 代码执行限制
    MAX_EXECUTION_TIME = 30  # 秒
    MAX_CODE_LENGTH = 10000  # 字符

    # 布局配置
    DEFAULT_2D_LAYOUT = "tree"
    DEFAULT_3D_LAYOUT = "spiral"

    # 可视化配置
    CANVAS_WIDTH = 800
    CANVAS_HEIGHT = 600


class DevelopmentConfig(Config):
    """开发环境配置"""

    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""

    DEBUG = False

    # 生产环境中的安全配置
    MAX_EXECUTION_TIME = 10  # 更短的执行时间限制
    MAX_CODE_LENGTH = 5000  # 更短的代码长度限制


class TestingConfig(Config):
    """测试环境配置"""

    TESTING = True
    DEBUG = True


# 配置字典
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
