# 数据库模块

数据库模块是一个简化的 SQLite 数据库管理器，专为音频处理系统设计，用于存储文件和任务的相关信息。

## 功能特点

### 核心功能
- **文件管理**：存储和检索文件信息
- **任务管理**：跟踪和更新任务状态
- **数据统计**：提供简单的统计信息
- **自动初始化**：启动时自动创建必要的数据库表

### 技术特点
- **轻量级**：使用 SQLite 作为存储引擎
- **简化接口**：提供直观的方法操作数据库
- **安全操作**：使用上下文管理器确保连接正确关闭
- **灵活配置**：支持自定义数据库文件路径

## 目录结构

```
database.py       # 数据库模块文件
app.db            # SQLite 数据库文件（自动生成）
```

## 数据库表结构

### 1. files 表

| 字段名 | 数据类型 | 描述 |
|--------|----------|------|
| `file_hash` | TEXT | 文件哈希值（主键） |
| `original_name` | TEXT | 文件原始名称 |
| `storage_path` | TEXT | 文件存储路径 |

### 2. tasks 表

| 字段名 | 数据类型 | 描述 |
|--------|----------|------|
| `task_id` | TEXT | 任务ID（主键） |
| `file_hash` | TEXT | 关联的文件哈希值 |
| `status` | TEXT | 任务状态（默认：pending） |
| `created_at` | TIMESTAMP | 任务创建时间（默认：当前时间） |

## 快速开始

### 基本使用

```python
from database import db

# 保存文件信息
db.save_file_info(
    file_hash="abc123",
    original_name="audio.mp3",
    storage_path="/path/to/storage/audio.mp3"
)

# 创建任务
db.create_task(
    task_id="task123",
    file_hash="abc123"
)

# 更新任务状态
db.update_task_status(
    task_id="task123",
    status="completed"
)
```

### 检查文件是否存在

```python
if db.check_file_exists("abc123"):
    print("文件已存在")
else:
    print("文件不存在")
```

### 获取文件信息

```python
file_info = db.get_file_info("abc123")
if file_info:
    print(f"文件名: {file_info['original_name']}")
    print(f"存储路径: {file_info['storage_path']}")
```

### 获取任务信息

```python
task_info = db.get_task("task123")
if task_info:
    print(f"任务状态: {task_info['status']}")
    print(f"创建时间: {task_info['created_at']}")
```

### 获取文件的所有任务

```python
tasks = db.get_file_tasks("abc123")
for task in tasks:
    print(f"任务ID: {task['task_id']}, 状态: {task['status']}")
```

### 获取统计信息

```python
stats = db.get_stats()
print(f"文件数量: {stats['files']}")
print(f"任务数量: {stats['tasks']}")
```

## 详细 API 文档

### 初始化

```python
# 使用默认数据库文件路径 (app.db)
db = FileDB()

# 自定义数据库文件路径
db = FileDB(db_path="custom.db")
```

### 文件操作

#### `check_file_exists(file_hash: str) -> bool`
检查文件是否已存在于数据库中。

**参数**：
- `file_hash`：文件的哈希值

**返回值**：
- `bool`：文件是否存在

#### `save_file_info(file_hash: str, original_name: str = None, storage_path: str = None)`
保存文件信息到数据库。

**参数**：
- `file_hash`：文件的哈希值（主键）
- `original_name`：文件的原始名称
- `storage_path`：文件的存储路径

#### `get_file_info(file_hash: str) -> Optional[Dict]`
获取文件信息。

**参数**：
- `file_hash`：文件的哈希值

**返回值**：
- `Dict`：文件信息字典，包含 `file_hash`、`original_name` 和 `storage_path` 字段
- `None`：如果文件不存在

### 任务操作

#### `create_task(task_id: str, file_hash: str)`
创建新任务。

**参数**：
- `task_id`：任务的唯一标识符
- `file_hash`：关联的文件哈希值

#### `update_task_status(task_id: str, status: str)`
更新任务状态。

**参数**：
- `task_id`：任务的唯一标识符
- `status`：新的任务状态（如 `pending`、`processing`、`completed`、`failed` 等）

#### `get_task(task_id: str) -> Optional[Dict]`
获取任务信息。

**参数**：
- `task_id`：任务的唯一标识符

**返回值**：
- `Dict`：任务信息字典，包含 `task_id`、`file_hash`、`status` 和 `created_at` 字段
- `None`：如果任务不存在

#### `get_file_tasks(file_hash: str) -> List[Dict]`
获取文件的所有任务。

**参数**：
- `file_hash`：文件的哈希值

**返回值**：
- `List[Dict]`：任务信息字典列表，按创建时间降序排列

### 统计方法

#### `get_stats() -> Dict`
获取简单的统计信息。

**返回值**：
- `Dict`：包含 `files` 和 `tasks` 字段，分别表示文件和任务的数量

## 集成到音频处理系统

### 示例：音频处理流程

```python
from database import db
import hashlib
import os

def process_audio(audio_path):
    # 1. 计算文件哈希
    with open(audio_path, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    
    # 2. 检查文件是否已处理
    if db.check_file_exists(file_hash):
        print("文件已处理过")
        return
    
    # 3. 保存文件信息
    db.save_file_info(
        file_hash=file_hash,
        original_name=os.path.basename(audio_path),
        storage_path=audio_path
    )
    
    # 4. 创建任务
    task_id = f"task_{file_hash}_{int(time.time())}"
    db.create_task(task_id=task_id, file_hash=file_hash)
    
    try:
        # 5. 处理音频
        print("处理音频中...")
        db.update_task_status(task_id, "processing")
        
        # 音频处理逻辑...
        
        # 6. 标记任务完成
        db.update_task_status(task_id, "completed")
        print("处理完成")
        
    except Exception as e:
        # 7. 标记任务失败
        db.update_task_status(task_id, "failed")
        print(f"处理失败: {e}")
```

## 数据库表结构详解

### files 表

| 字段名 | 数据类型 | 约束 | 描述 |
|--------|----------|------|------|
| `file_hash` | TEXT | PRIMARY KEY | 文件的唯一标识符，通常是文件内容的哈希值 |
| `original_name` | TEXT | | 文件的原始名称，便于用户识别 |
| `storage_path` | TEXT | | 文件在系统中的存储路径 |

### tasks 表

| 字段名 | 数据类型 | 约束 | 描述 |
|--------|----------|------|------|
| `task_id` | TEXT | PRIMARY KEY | 任务的唯一标识符 |
| `file_hash` | TEXT | NOT NULL | 关联的文件哈希值，用于与 files 表关联 |
| `status` | TEXT | DEFAULT 'pending' | 任务状态，如 pending、processing、completed、failed 等 |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 任务创建时间，自动设置为当前时间 |

## 最佳实践

### 1. 文件哈希计算

建议使用文件内容的 MD5 或 SHA256 哈希值作为 `file_hash`：

```python
import hashlib

def calculate_file_hash(file_path):
    """计算文件的 MD5 哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b"" ):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
```

### 2. 任务状态管理

建议使用以下任务状态：

| 状态 | 描述 |
|------|------|
| `pending` | 任务已创建，但尚未开始处理 |
| `processing` | 任务正在处理中 |
| `completed` | 任务处理成功完成 |
| `failed` | 任务处理失败 |

### 3. 错误处理

使用 try-except 块捕获数据库操作可能的错误：

```python
try:
    db.save_file_info(file_hash, original_name, storage_path)
except Exception as e:
    print(f"保存文件信息失败: {e}")
```

### 4. 性能考虑

对于大量文件和任务，考虑以下优化：
- 批量操作：使用事务批量处理多个记录
- 索引：为频繁查询的字段添加索引
- 清理：定期清理不再需要的旧数据

## 故障排除

### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 数据库文件创建失败 | 权限不足 | 确保程序有写入权限 |
| 连接失败 | 数据库文件被占用 | 确保只有一个进程访问数据库 |
| 查询无结果 | 数据不存在或查询条件错误 | 检查参数是否正确 |
| 插入失败 | 违反唯一约束 | 使用 `INSERT OR IGNORE` 或检查数据是否已存在 |

### 日志查看

数据库操作会生成日志信息，可以通过配置日志级别查看详细信息：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 版本历史

### v1.0.0
- 初始版本
- 实现文件和任务管理功能
- 提供基本的统计方法

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 联系信息

如有问题或建议，请通过以下方式联系：
- 项目维护者 qdooo-w

---

**✨ 由 数据库模块 团队开发**
