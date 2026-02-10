#!/usr/bin/env python3
"""
数据库初始化程序
用于创建数据库和表结构，确保系统启动时数据库结构正确

功能：
- 创建SQLite数据库文件
- 创建必要的表结构（files和tasks表）
- 创建索引以提高性能
- 提供重置数据库的选项
- 显示初始化过程的日志信息
"""

import sqlite3
import logging
import os
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self, db_path: str = "../app.db"):
        """
        初始化数据库初始化器
        
        :param db_path: 数据库文件路径
        """
        # 确保目标目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"创建数据库目录: {db_dir}")
        
        self.db_path = os.path.abspath(db_path)
        logger.info(f"数据库初始化器创建，目标路径: {self.db_path}")
    
    def init_database(self, reset: bool = False):
        """
        初始化数据库
        
        :param reset: 是否重置数据库（删除现有文件）
        :return: bool - 初始化是否成功
        """
        try:
            # 检查数据库文件是否存在
            db_exists = os.path.exists(self.db_path)
            
            if db_exists and reset:
                logger.info("重置数据库：删除现有数据库文件")
                os.remove(self.db_path)
                db_exists = False
            
            if db_exists:
                logger.info("数据库文件已存在，检查表结构")
                return self._check_and_update_schema()
            else:
                logger.info("创建新的数据库文件")
                return self._create_schema()
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            return False
    
    def _get_conn(self):
        """
        获取数据库连接
        
        :return: sqlite3.Connection - 数据库连接
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_schema(self):
        """
        创建数据库表结构
        
        :return: bool - 创建是否成功
        """
        try:
            with self._get_conn() as conn:
                logger.info("开始创建表结构")
                
                # 创建files表
                logger.info("创建files表")
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
                
                # 创建tasks表
                logger.info("创建tasks表")
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
                        UNIQUE(file_hash, task_type)
                    )
                ''')
                
                # 创建索引
                logger.info("创建索引")
                conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_file ON tasks(file_hash)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
                
                conn.commit()
                logger.info("表结构创建完成")
                
                # 验证表结构
                self._verify_schema(conn)
                
                return True
                
        except Exception as e:
            logger.error(f"创建表结构失败: {e}")
            return False
    
    def _check_and_update_schema(self):
        """
        检查并更新数据库表结构
        
        :return: bool - 检查和更新是否成功
        """
        try:
            with self._get_conn() as conn:
                logger.info("检查表结构")
                
                # 验证表结构
                if self._verify_schema(conn):
                    logger.info("表结构完整，无需更新")
                    return True
                else:
                    logger.info("表结构不完整，需要更新")
                    # 更新表结构
                    self._update_schema(conn)
                    return True
                    
        except Exception as e:
            logger.error(f"检查表结构失败: {e}")
            return False
    
    def _update_schema(self, conn):
        """
        更新数据库表结构
        
        :param conn: sqlite3.Connection - 数据库连接
        """
        try:
            # 检查并添加files表的processed_operations列
            cursor = conn.execute("PRAGMA table_info(files)")
            files_columns = [row[1] for row in cursor.fetchall()]
            
            if 'processed_operations' not in files_columns:
                logger.info("添加files表的processed_operations列")
                conn.execute('''
                    ALTER TABLE files ADD COLUMN processed_operations TEXT DEFAULT '{}'
                ''')
                logger.info("processed_operations列添加成功")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"更新表结构失败: {e}")
            conn.execute('ROLLBACK')
            raise
    
    def _verify_schema(self, conn):
        """
        验证数据库表结构
        
        :param conn: sqlite3.Connection - 数据库连接
        :return: bool - 表结构是否完整
        """
        try:
            # 检查files表
            cursor = conn.execute("PRAGMA table_info(files)")
            files_columns = [row[1] for row in cursor.fetchall()]
            
            required_files_columns = [
                'file_hash', 'original_name', 'storage_path',
                'upload_time', 'upload_count', 'processed_operations'
            ]
            
            for col in required_files_columns:
                if col not in files_columns:
                    logger.warning(f"files表缺少列: {col}")
                    return False
            
            # 检查tasks表
            cursor = conn.execute("PRAGMA table_info(tasks)")
            tasks_columns = [row[1] for row in cursor.fetchall()]
            
            required_tasks_columns = [
                'task_id', 'file_hash', 'task_type', 'status',
                'created_at', 'started_at', 'completed_at',
                'result_path', 'error_message'
            ]
            
            for col in required_tasks_columns:
                if col not in tasks_columns:
                    logger.warning(f"tasks表缺少列: {col}")
                    return False
            
            # 检查索引
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            required_indexes = [
                'idx_tasks_file', 'idx_tasks_type', 'idx_tasks_status'
            ]
            
            for idx in required_indexes:
                if idx not in indexes:
                    logger.warning(f"缺少索引: {idx}")
                    # 这里可以添加创建索引的逻辑
            
            logger.info("表结构验证通过")
            return True
            
        except Exception as e:
            logger.error(f"验证表结构失败: {e}")
            return False
    
    def get_stats(self):
        """
        获取数据库统计信息
        
        :return: dict - 统计信息
        """
        try:
            with self._get_conn() as conn:
                # 获取文件数量
                cursor = conn.execute("SELECT COUNT(*) FROM files")
                files_count = cursor.fetchone()[0]
                
                # 获取任务数量
                cursor = conn.execute("SELECT COUNT(*) FROM tasks")
                tasks_count = cursor.fetchone()[0]
                
                # 获取任务状态统计
                cursor = conn.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
                task_status_stats = {}
                for row in cursor.fetchall():
                    task_status_stats[row[0]] = row[1]
                
                return {
                    "database_path": self.db_path,
                    "files_count": files_count,
                    "tasks_count": tasks_count,
                    "task_status_stats": task_status_stats,
                    "file_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                }
                
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def clear_data(self):
        """
        清空数据库数据（保留表结构）
        
        :return: bool - 清空是否成功
        """
        try:
            with self._get_conn() as conn:
                logger.info("清空数据库数据")
                
                # 先删除tasks表数据
                conn.execute("DELETE FROM tasks")
                
                # 再删除files表数据
                conn.execute("DELETE FROM files")
                
                conn.commit()
                logger.info("数据库数据清空成功")
                return True
                
        except Exception as e:
            logger.error(f"清空数据库数据失败: {e}")
            return False

def main():
    """
    主函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='数据库初始化程序')
    
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 设置默认数据库路径为项目根目录
    default_db_path = os.path.join(script_dir, '..', 'app.db')
    
    parser.add_argument('--db', type=str, default=default_db_path,
                      help='数据库文件路径')
    parser.add_argument('--reset', action='store_true',
                      help='重置数据库（删除现有文件）')
    parser.add_argument('--clear', action='store_true',
                      help='清空数据库数据（保留表结构）')
    parser.add_argument('--stats', action='store_true',
                      help='获取数据库统计信息')
    
    args = parser.parse_args()
    
    # 创建初始化器
    initializer = DatabaseInitializer(args.db)
    
    # 执行相应操作
    if args.clear:
        # 清空数据
        if initializer.clear_data():
            logger.info("数据清空成功")
        else:
            logger.error("数据清空失败")
    elif args.stats:
        # 获取统计信息
        stats = initializer.get_stats()
        if stats:
            logger.info("数据库统计信息:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")
        else:
            logger.error("获取统计信息失败")
    else:
        # 初始化数据库
        if initializer.init_database(args.reset):
            logger.info("数据库初始化成功")
            
            # 显示统计信息
            stats = initializer.get_stats()
            if stats:
                logger.info("初始化后统计信息:")
                for key, value in stats.items():
                    logger.info(f"  {key}: {value}")
        else:
            logger.error("数据库初始化失败")

if __name__ == "__main__":
    main()
