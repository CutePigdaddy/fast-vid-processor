"""
SQLite数据库操作模块
- files 表：file_hash (PK) + status (progress/success/failed)
- tasks 表：task_id (PK) -> file_hash 映射，用于通过 Celery task_id 反查 hash
"""
import sqlite3
import logging
from typing import Optional, List, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileDB:
    """SQLite数据库管理器 —— hash-based 文件去重 + 任务映射"""
    
    def __init__(self, db_path: str = "app.db"):
        self.db_path = db_path
        self._init_db()
    
    def _get_conn(self):
        """获取数据库连接（启用 WAL 模式提升并发性能）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            # files 表：以 file_hash 为主键，status 记录处理状态
            conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    file_hash TEXT PRIMARY KEY,
                    status TEXT DEFAULT 'progress'
                )
            ''')
            
            # tasks 表：task_id -> file_hash 映射，用于从 Celery 回调中反查 hash
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("数据库表初始化完成")
    
    # ===== 文件操作 =====
    
    def check_file_exists(self, file_hash: str) -> bool:
        """检查文件哈希是否已存在"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM files WHERE file_hash = ?", 
                (file_hash,)
            )
            return cursor.fetchone() is not None
    
    def get_file_status(self, file_hash: str) -> Optional[str]:
        """获取文件的处理状态，不存在返回 None"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT status FROM files WHERE file_hash = ?",
                (file_hash,)
            )
            row = cursor.fetchone()
            return row["status"] if row else None
    
    def save_file_record(self, file_hash: str, status: str = "progress"):
        """插入新的文件记录（初始状态 progress）"""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO files (file_hash, status) VALUES (?, ?)",
                (file_hash, status)
            )
            conn.commit()
    
    def update_file_status(self, file_hash: str, status: str):
        """更新文件的处理状态 (progress / success / failed)"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE files SET status = ? WHERE file_hash = ?",
                (status, file_hash)
            )
            conn.commit()
    
    # ===== 任务映射操作 =====
    
    def create_task(self, task_id: str, file_hash: str):
        """创建 task_id -> file_hash 映射"""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO tasks (task_id, file_hash) VALUES (?, ?)",
                (task_id, file_hash)
            )
            conn.commit()
    
    def get_hash_by_task(self, task_id: str) -> Optional[str]:
        """通过 task_id 反查 file_hash"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT file_hash FROM tasks WHERE task_id = ?",
                (task_id,)
            )
            row = cursor.fetchone()
            return row["file_hash"] if row else None
    
    def get_task_id_by_hash(self, file_hash: str) -> Optional[str]:
        """通过 file_hash 查询最新的 task_id"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT task_id FROM tasks WHERE file_hash = ? ORDER BY created_at DESC LIMIT 1",
                (file_hash,)
            )
            row = cursor.fetchone()
            return row["task_id"] if row else None
    
    # ===== 统计 =====
    
    def get_stats(self):
        """获取简单统计"""
        with self._get_conn() as conn:
            files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            return {"files": files, "tasks": tasks}


# 创建全局数据库实例
db = FileDB()