import logging
import os
import aiofiles
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from celery.result import AsyncResult
from tasks import text_task, app as celery_app
from config import settings
from modules.database import db

# 设置详细日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/tasks/text")
async def create_text_task(file: UploadFile = File(...)):
    """
    上传视频并创建 to_text 任务。
    前端已将文件名设为 <SHA256_HASH><ext>，后端信任该哈希值。
    
    流程：
    1. 从文件名提取哈希值
    2. 查 SQLite 判断是否已处理过
       - success → 直接返回已完成
       - progress → 返回处理中（附带 task_id 供前端轮询）
       - failed / 不存在 → 保存文件并下发新任务
    """
    filename = file.filename or ''
    name_without_ext, ext = os.path.splitext(filename)
    file_hash = name_without_ext  # 文件名就是哈希值
    
    if not file_hash:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    logger.info(f"[{file_hash}] 收到上传请求, 扩展名: {ext}")

    try:
        # 查询数据库中的状态
        existing_status = db.get_file_status(file_hash)
        
        if existing_status == "success":
            logger.info(f"[{file_hash}] 文件已处理完成，直接返回")
            return {
                "status": "completed",
                "file_hash": file_hash,
                "message": "该文件已处理完成"
            }
        
        if existing_status == "progress":
            # 正在处理中，查找已有的 task_id 返回给前端用于轮询
            task_id = db.get_task_id_by_hash(file_hash)
            logger.info(f"[{file_hash}] 文件正在处理中, task_id: {task_id}")
            return {
                "status": "processing",
                "file_hash": file_hash,
                "task_id": task_id,
                "message": "该文件正在处理中"
            }
        
        # failed 或不存在 → 需要（重新）处理
        # 创建目录结构
        settings.ensure_hash_dirs(file_hash)
        
        # 保存源文件到 data/<HASH>/source/<HASH><ext>
        source_dir = settings.get_source_dir(settings.DATA_DIR, file_hash)
        save_path = os.path.join(source_dir, f"{file_hash}{ext}")
        
        logger.info(f"[{file_hash}] 正在保存到: {save_path}")
        async with aiofiles.open(save_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunk
                if not chunk:
                    break
                await buffer.write(chunk)
        logger.info(f"[{file_hash}] 文件保存成功")
        
        # 写入/更新数据库记录
        if existing_status == "failed":
            db.update_file_status(file_hash, "progress")
        else:
            db.save_file_record(file_hash, status="progress")
        
        # 下发 Celery 任务
        result = text_task.delay(file_hash)
        task_id = result.id
        
        # 记录 task_id -> file_hash 映射
        db.create_task(task_id, file_hash)
        
        logger.info(f"[{file_hash}] Celery 任务已下发, task_id: {task_id}")
        
        return {
            "status": "processing",
            "file_hash": file_hash,
            "task_id": task_id,
            "message": "任务已创建"
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[{file_hash}] 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/{file_hash}/status")
def get_file_status(file_hash: str):
    """
    查询文件处理状态。
    - SQLite 中 status == 'success' → 直接返回完成（不查 Redis）
    - SQLite 中 status == 'progress' → 查 Redis 获取 Celery 实时状态
    - SQLite 中 status == 'failed' → 返回失败
    - 不存在 → 404
    """
    existing_status = db.get_file_status(file_hash)
    
    if existing_status is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if existing_status == "success":
        # 已完成，返回各输出文件是否存在
        text_dir = settings.get_text_dir(settings.DATA_DIR, file_hash)
        track_dir = settings.get_track_dir(settings.DATA_DIR, file_hash)
        vocal_dir = settings.get_vocal_dir(settings.DATA_DIR, file_hash)
        
        return {
            "status": "success",
            "file_hash": file_hash,
            "files": {
                "text": os.path.exists(os.path.join(text_dir, f"{file_hash}.txt")),
                "track": os.path.exists(os.path.join(track_dir, f"{file_hash}.mp3")),
                "vocal": os.path.exists(os.path.join(vocal_dir, f"{file_hash}.mp3")),
            }
        }
    
    if existing_status == "failed":
        return {
            "status": "failed",
            "file_hash": file_hash,
        }
    
    # progress → 查 Celery 获取细粒度状态
    task_id = db.get_task_id_by_hash(file_hash)
    if not task_id:
        return {
            "status": "progress",
            "file_hash": file_hash,
            "celery_status": "UNKNOWN"
        }
    
    result = AsyncResult(task_id, app=celery_app)
    
    # 映射 Celery 状态
    celery_status = result.status  # PENDING, STARTED, separated, distracted, converted, SUCCESS, FAILURE
    celery_meta = None
    
    if result.status == "FAILURE":
        # Celery 标记失败但 SQLite 可能还没更新（竞态条件），同步一下
        db.update_file_status(file_hash, "failed")
        return {
            "status": "failed",
            "file_hash": file_hash,
        }
    
    if result.status == "SUCCESS":
        # Celery 标记成功但 SQLite 可能还没更新，同步一下
        db.update_file_status(file_hash, "success")
        return {
            "status": "success",
            "file_hash": file_hash,
            "files": {
                "text": True,
                "track": True,
                "vocal": True,
            }
        }
    
    # 处理中 —— 返回 Celery 的自定义中间状态
    if hasattr(result, 'info') and isinstance(result.info, dict):
        celery_meta = result.info
    
    return {
        "status": "progress",
        "file_hash": file_hash,
        "celery_status": celery_status,
        "meta": celery_meta
    }


@app.get("/files/{file_hash}/download/{file_type}")
def download_file(file_hash: str, file_type: str):
    """
    下载处理后的文件。
    file_type: text / track / vocal / source
    """
    # 检查文件是否存在于数据库
    if not db.check_file_exists(file_hash):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 根据 file_type 确定路径
    type_map = {
        "text": (settings.get_text_dir, f"{file_hash}.txt"),
        "track": (settings.get_track_dir, f"{file_hash}.mp3"),
        "vocal": (settings.get_vocal_dir, f"{file_hash}.mp3"),
    }
    
    if file_type == "source":
        import glob
        source_dir = settings.get_source_dir(settings.DATA_DIR, file_hash)
        files = glob.glob(os.path.join(source_dir, f"{file_hash}.*"))
        if not files:
            raise HTTPException(status_code=404, detail="源文件不存在")
        file_path = files[0]
    elif file_type in type_map:
        dir_fn, filename = type_map[file_type]
        file_path = os.path.join(dir_fn(settings.DATA_DIR, file_hash), filename)
    else:
        raise HTTPException(status_code=400, detail="无效的文件类型，支持: text, track, vocal, source")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件尚未生成或不存在")

    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type='application/octet-stream'
    )


@app.get("/files/{file_hash}/text")
def get_text_content(file_hash: str):
    """
    直接获取转写文本内容（前端展示用）。
    """
    status = db.get_file_status(file_hash)
    if status != "success":
        raise HTTPException(status_code=404, detail="文件尚未处理完成")
    
    text_dir = settings.get_text_dir(settings.DATA_DIR, file_hash)
    text_path = os.path.join(text_dir, f"{file_hash}.txt")
    
    if not os.path.exists(text_path):
        raise HTTPException(status_code=404, detail="文本文件不存在")
    
    with open(text_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {
        "file_hash": file_hash,
        "text_content": content
    }