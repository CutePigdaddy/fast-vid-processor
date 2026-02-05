import os

class Config:
    # Celery 配置
    CELERY_BROKER_URL = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = "redis://localhost:6379/1"

    # 路径配置
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    
    # 其他全局变量
    ALLOWED_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov'}

# 导出实例供直接使用
settings = Config()