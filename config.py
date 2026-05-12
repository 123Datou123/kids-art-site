"""
配置文件
所有可调参数集中在这里，方便后续扩展
"""
import os


class Config:
    # Flask 设置
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-please-change-in-production")

    # 默认图片源：wikimedia（无需 API 密钥）或 pixabay（需注册免费 API key）
    DEFAULT_SOURCE = os.environ.get("DEFAULT_SOURCE", "wikimedia")

    # Pixabay 配置（可选）—— 在 https://pixabay.com/api/docs/ 免费注册
    PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")

    # 线稿生成最大边长（避免超大图拖慢处理）
    LINEART_MAX_SIZE = 1200
