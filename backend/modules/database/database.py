"""
SQLite数据库操作模块
所有文件、任务的数据存储都在这里
"""
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileDB:
    """简化的SQLite数据库管理器"""
    
    def __init__(self, db_path: str = "app.db"):
        self.db_path = db_path
        self._init_db()
    
    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使返回结果为字典格式
        return conn
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            # 创建files表（只有3个字段）
            conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    file_hash TEXT PRIMARY KEY,
                    original_name TEXT,
                    storage_path TEXT
                )
            ''')
            
            # 创建tasks表（4个字段）
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("数据库表创建完成")
    
    # ===== 文件操作 =====
    
    def check_file_exists(self, file_hash: str) -> bool:
        """检查文件是否已存在"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM files WHERE file_hash = ?", 
                (file_hash,)
            )
            return cursor.fetchone() is not None
    
    def save_file_info(self, file_hash: str, original_name: str = None, storage_path: str = None):
        """保存文件信息到数据库"""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO files VALUES (?, ?, ?)",
                (file_hash, original_name, storage_path)
            )
            conn.commit()
    
    def get_file_info(self, file_hash: str) -> Optional[Dict]:
        """获取文件信息"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM files WHERE file_hash = ?", 
                (file_hash,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ===== 任务操作 =====
    
    def create_task(self, task_id: str, file_hash: str):
        """创建新任务"""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO tasks (task_id, file_hash) VALUES (?, ?)",
                (task_id, file_hash)
            )
            conn.commit()
    
    def update_task_status(self, task_id: str, status: str):
        """更新任务状态"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status = ? WHERE task_id = ?",
                (status, task_id)
            )
            conn.commit()
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务信息"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?", 
                (task_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_file_tasks(self, file_hash: str) -> List[Dict]:
        """获取文件的所有任务"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE file_hash = ? ORDER BY created_at DESC", 
                (file_hash,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # ===== 统计和工具方法 =====
    
    def get_stats(self):
        """获取简单统计"""
        with self._get_conn() as conn:
            files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            
            return {
                "files": files,
                "tasks": tasks
            }

# 创建全局数据库实例
db = FileDB()