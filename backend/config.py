import os

class Config:
    # --- Redis / Celery 配置 ---
    # 优先从环境变量获取，如果没有(比如本地运行)，则默认为 localhost
    # 在 Docker Compose 中，我们会注入 'redis://redis:6379/0'
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    # --- 路径配置 ---
    # 基础目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # 数据根目录：优先使用环境变量 DATA_DIR (Docker 中设为 /data)，否则在本地项目下生成 data 文件夹
    DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))

    # 输入(上传)文件存放处
    DEFAULT_INPUT_SAVE_DIR = os.path.join(DATA_DIR, "uploads")
    
    # 输出(处理结果)文件存放处
    DEFAULT_OUTPUT_DIR = os.path.join(DATA_DIR, "processed")
    
    # --- 其他配置 ---
    ALLOWED_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov'}
    TRACK_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "track")
    AUDIO_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "audio")
    TEXT_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "text")
    # 自动创建必要目录（防止报错）
    def ensure_dirs(self):
        os.makedirs(self.DEFAULT_INPUT_SAVE_DIR, exist_ok=True)
        os.makedirs(self.DEFAULT_OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.TRACK_DIR, exist_ok=True)
        os.makedirs(self.AUDIO_DIR, exist_ok=True)
        os.makedirs(self.TEXT_DIR, exist_ok=True)

# 导出实例
settings = Config()
# 初始化时确保目录存在
settings.ensure_dirs()