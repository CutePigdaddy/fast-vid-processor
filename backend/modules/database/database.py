"""
数据库模块 - 管理文件和任务信息
作者：你
日期：今天
功能：文件去重 + 任务去重 + 状态管理
"""
import sqlite3
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileDB:
    """音视频处理数据库管理器"""
    
    def __init__(self, db_path: str = "app.db"):
        """
        初始化数据库
        :param db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()
        logger.info(f"数据库初始化完成: {db_path}")
    
    def _get_conn(self):
        """获取数据库连接（自动关闭）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        return conn
    
    def _init_db(self):
        """创建数据库表（如果不存在）"""
        with self._get_conn() as conn:
            # 1. 创建files表 - 存储文件信息
            conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    file_hash TEXT PRIMARY KEY,
                    original_name TEXT,
                    storage_path TEXT,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    upload_count INTEGER DEFAULT 1,
                    processed_operations TEXT DEFAULT '{}'
                )
            ''')
            
            # 2. 创建tasks表 - 存储任务信息
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    result_path TEXT,
                    error_message TEXT,
                    UNIQUE(file_hash, task_type)  -- 关键：防止重复任务
                )
            ''')
            
            # 3. 创建索引提高查询速度
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_file ON tasks(file_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
            
            conn.commit()
    
    # ==================== 文件操作 ====================
    
    def check_file_exists(self, file_hash: str) -> bool:
        """
        检查文件是否已存在
        :param file_hash: 文件哈希值
        :return: True如果文件已存在
        """
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT 1 FROM files WHERE file_hash = ?", (file_hash,))
            return cursor.fetchone() is not None
    
    def save_file_info(self, file_hash: str, original_name: str = None, storage_path: str = None) -> bool:
        """
        保存文件信息
        :param file_hash: 文件哈希
        :param original_name: 原始文件名
        :param storage_path: 存储路径
        :return: True如果成功，False如果文件已存在
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO files (file_hash, original_name, storage_path) VALUES (?, ?, ?)",
                    (file_hash, original_name, storage_path)
                )
                conn.commit()
                logger.info(f"文件保存成功: {file_hash}")
                return True
        except sqlite3.IntegrityError:
            logger.info(f"文件已存在，跳过保存: {file_hash}")
            return False
    
    def increment_upload_count(self, file_hash: str):
        """增加文件上传次数（用于统计）"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE files SET upload_count = upload_count + 1 WHERE file_hash = ?",
                (file_hash,)
            )
            conn.commit()
    
    def get_file_info(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM files WHERE file_hash = ?", (file_hash,))
            row = cursor.fetchone()
            if not row:
                return None
            
            file_info = dict(row)
            # 解析processed_operations字段
            import json
            try:
                file_info['processed_operations'] = json.loads(file_info['processed_operations'])
            except json.JSONDecodeError:
                file_info['processed_operations'] = {}
            
            return file_info
    
    def update_processed_operation(self, file_hash: str, operation: str, status: str = "completed", result_path: str = None, completed_at: str = None):
        """
        更新文件的处理操作状态
        :param file_hash: 文件哈希
        :param operation: 操作类型（如 extract_audio, transcribe, ai_summarize）
        :param status: 操作状态（completed, failed, in_progress）
        :param result_path: 结果文件路径
        :param completed_at: 完成时间
        """
        import json
        
        # 获取当前的处理操作
        file_info = self.get_file_info(file_hash)
        if not file_info:
            logger.error(f"文件不存在: {file_hash}")
            return False
        
        operations = file_info.get('processed_operations', {})
        
        # 更新操作信息
        operations[operation] = {
            "status": status,
            "result_path": result_path,
            "completed_at": completed_at or datetime.now().isoformat()
        }
        
        # 将操作信息转换为JSON字符串并保存
        operations_json = json.dumps(operations)
        
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE files SET processed_operations = ? WHERE file_hash = ?",
                (operations_json, file_hash)
            )
            conn.commit()
            logger.info(f"更新文件处理操作: {file_hash} -> {operation}: {status}")
            return True
    
    def get_processed_operations(self, file_hash: str) -> Dict[str, Any]:
        """
        获取文件的所有处理操作
        :param file_hash: 文件哈希
        :return: 处理操作字典
        """
        file_info = self.get_file_info(file_hash)
        if not file_info:
            return {}
        
        return file_info.get('processed_operations', {})
    
    def has_operation_completed(self, file_hash: str, operation: str) -> bool:
        """
        检查特定操作是否已完成
        :param file_hash: 文件哈希
        :param operation: 操作类型
        :return: True如果操作已完成
        """
        operations = self.get_processed_operations(file_hash)
        operation_info = operations.get(operation, {})
        return operation_info.get('status') == 'completed'
    
    def remove_processed_operation(self, file_hash: str, operation: str):
        """
        移除文件的特定处理操作
        :param file_hash: 文件哈希
        :param operation: 操作类型
        """
        import json
        
        # 获取当前的处理操作
        file_info = self.get_file_info(file_hash)
        if not file_info:
            logger.error(f"文件不存在: {file_hash}")
            return False
        
        operations = file_info.get('processed_operations', {})
        
        # 移除指定操作
        if operation in operations:
            del operations[operation]
        
        # 将操作信息转换为JSON字符串并保存
        operations_json = json.dumps(operations)
        
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE files SET processed_operations = ? WHERE file_hash = ?",
                (operations_json, file_hash)
            )
            conn.commit()
            logger.info(f"移除文件处理操作: {file_hash} -> {operation}")
            return True
    
    # ==================== 任务操作 ====================
    
    def create_task(self, task_id: str, file_hash: str, task_type: str = "transcribe") -> bool:
        """
        创建新任务（如果同类型任务已存在会失败）
        :param task_id: 任务ID（UUID）
        :param file_hash: 文件哈希
        :param task_type: 任务类型（extract_audio, transcribe, ai_summarize, extract_keyframes）
        :return: True如果创建成功，False如果任务已存在
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO tasks (task_id, file_hash, task_type) VALUES (?, ?, ?)",
                    (task_id, file_hash, task_type)
                )
                conn.commit()
                logger.info(f"任务创建成功: {task_id} ({task_type})")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"任务已存在，跳过创建: {file_hash} -> {task_type}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """根据任务ID获取任务信息"""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def find_task(self, file_hash: str, task_type: str) -> Optional[Dict[str, Any]]:
        """查找特定文件的特定类型任务"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE file_hash = ? AND task_type = ?",
                (file_hash, task_type)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_task_started(self, task_id: str):
        """标记任务开始执行"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status = 'running', started_at = CURRENT_TIMESTAMP WHERE task_id = ?",
                (task_id,)
            )
            conn.commit()
            logger.info(f"任务开始: {task_id}")
    
    def update_task_completed(self, task_id: str, status: str, result_path: str = None, error_message: str = None):
        """
        标记任务完成
        :param task_id: 任务ID
        :param status: 状态（success 或 failed）
        :param result_path: 结果文件路径
        :param error_message: 错误信息
        """
        with self._get_conn() as conn:
            # 获取任务信息（用于更新文件的处理操作）
            cursor = conn.execute("SELECT file_hash, task_type FROM tasks WHERE task_id = ?", (task_id,))
            task_info = cursor.fetchone()
            
            if status == "success":
                conn.execute(
                    "UPDATE tasks SET status = ?, completed_at = CURRENT_TIMESTAMP, result_path = ? WHERE task_id = ?",
                    (status, result_path, task_id)
                )
                logger.info(f"任务成功完成: {task_id}")
            else:
                conn.execute(
                    "UPDATE tasks SET status = ?, completed_at = CURRENT_TIMESTAMP, error_message = ? WHERE task_id = ?",
                    (status, error_message, task_id)
                )
                logger.error(f"任务失败: {task_id} - {error_message}")
            conn.commit()
        
        # 自动更新文件的处理操作信息
        if task_info:
            file_hash = task_info["file_hash"]
            task_type = task_info["task_type"]
            
            # 更新文件的处理操作状态
            operation_status = "completed" if status == "success" else "failed"
            self.update_processed_operation(
                file_hash=file_hash,
                operation=task_type,
                status=operation_status,
                result_path=result_path,
                completed_at=datetime.now().isoformat()
            )
    
    def get_file_tasks(self, file_hash: str) -> List[Dict[str, Any]]:
        """获取文件的所有任务"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT task_id, task_type, status, result_path FROM tasks WHERE file_hash = ? ORDER BY created_at",
                (file_hash,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== 统计和工具方法 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        with self._get_conn() as conn:
            # 文件统计
            cursor = conn.execute("SELECT COUNT(*) as count FROM files")
            file_count = cursor.fetchone()["count"]
            
            # 任务统计
            cursor = conn.execute("SELECT task_type, status, COUNT(*) as count FROM tasks GROUP BY task_type, status")
            tasks = cursor.fetchall()
            
            # 组织成易读的格式
            task_stats = {}
            for task in tasks:
                task_type = task["task_type"]
                status = task["status"]
                if task_type not in task_stats:
                    task_stats[task_type] = {}
                task_stats[task_type][status] = task["count"]
            
            return {
                "files": file_count,
                "tasks": task_stats
            }
    
    def cleanup_old_data(self, days: int = 30):
        """清理指定天数前的失败任务（可选）"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM tasks WHERE status = 'failed' AND created_at < datetime('now', ?)",
                (f'-{days} days',)
            )
            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"清理了 {deleted} 条旧的失败任务记录")

# ==================== 使用示例 ====================

# 创建全局数据库实例（整个应用用一个实例）
db = FileDB()

def demo_usage():
    """演示如何使用数据库"""
    print("=== 数据库使用演示 ===")
    
    # 1. 保存文件信息
    file_hash = "abc123def456"
    db.save_file_info(file_hash, "my_video.mp4", f"/uploads/{file_hash}/original.mp4")
    
    # 2. 检查文件是否存在
    if db.check_file_exists(file_hash):
        print(f"文件 {file_hash} 已存在")
    
    # 3. 创建任务
    task_id = "task-001"
    task_type = "extract_audio"
    created = db.create_task(task_id, file_hash, task_type)
    if created:
        print(f"创建了任务: {task_id}")
    
    # 4. 更新任务状态
    db.update_task_started(task_id)
    # 模拟处理...
    db.update_task_completed(task_id, "success", f"/uploads/{file_hash}/audio.mp3")
    
    # 5. 查询文件的所有任务
    tasks = db.get_file_tasks(file_hash)
    print(f"文件 {file_hash} 的任务:")
    for task in tasks:
        print(f"  - {task['task_type']}: {task['status']}")
    
    # 6. 获取统计信息
    stats = db.get_stats()
    print(f"\n系统统计:")
    print(f"  文件总数: {stats['files']}")
    for task_type, status_counts in stats['tasks'].items():
        print(f"  {task_type}: {status_counts}")

if __name__ == "__main__":
    # 运行演示
    demo_usage()