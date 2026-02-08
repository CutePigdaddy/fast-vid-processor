import os

class Config:
    # --- Redis / Celery 配置 ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    # --- 路径配置 ---
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # 数据根目录：Docker 中为 /data，本地为 backend/data
    DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))

    # --- 其他配置 ---
    ALLOWED_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov'}

    # ===== Hash-based 路径工具方法 =====
    
    @staticmethod
    def get_hash_dir(data_dir: str, file_hash: str) -> str:
        """获取某个 hash 对应的根目录: data/<HASH>/"""
        return os.path.join(data_dir, file_hash)
    
    @staticmethod
    def get_source_dir(data_dir: str, file_hash: str) -> str:
        """源文件目录: data/<HASH>/source/"""
        return os.path.join(data_dir, file_hash, "source")
    
    @staticmethod
    def get_track_dir(data_dir: str, file_hash: str) -> str:
        """音轨目录: data/<HASH>/track/"""
        return os.path.join(data_dir, file_hash, "track")
    
    @staticmethod
    def get_vocal_dir(data_dir: str, file_hash: str) -> str:
        """人声目录: data/<HASH>/vocal/"""
        return os.path.join(data_dir, file_hash, "vocal")
    
    @staticmethod
    def get_text_dir(data_dir: str, file_hash: str) -> str:
        """文本目录: data/<HASH>/text/"""
        return os.path.join(data_dir, file_hash, "text")
    
    def ensure_hash_dirs(self, file_hash: str):
        """为某个 hash 创建完整的目录结构"""
        for dir_fn in [self.get_source_dir, self.get_track_dir, self.get_vocal_dir, self.get_text_dir]:
            os.makedirs(dir_fn(self.DATA_DIR, file_hash), exist_ok=True)

    def ensure_data_dir(self):
        """确保数据根目录存在"""
        os.makedirs(self.DATA_DIR, exist_ok=True)

# 导出实例
settings = Config()
# 初始化时确保数据根目录存在
settings.ensure_data_dir()