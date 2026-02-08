import logging
import os
import aiofiles
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from celery import uuid
from celery.result import AsyncResult
from tasks import (
    text_task, 
    photo_task, 
    extract_audio_task, 
    vocal_task, 
    stt_task, 
    app as celery_app
)  # type: ignore
from config import settings

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

@app.post("/tasks/{task_type}")
async def create_task(task_type: str, file: UploadFile = File(...)):
  """
  创建一个新任务的 API 端点。
  支持: "text", "photo", "text_and_audio", "extract_audio", "vocal_extraction", "stt"。
  """
  file_uuid = uuid()
  logger.info(f"[{file_uuid}] 收到上传请求. 文件名: {file.filename}, 任务类型: {task_type}")

  try:
    # 路径处理
    _, ext = os.path.splitext(file.filename or '')
    base_dir = settings.DEFAULT_INPUT_SAVE_DIR
    
    # 确保目录存在
    os.makedirs(base_dir, exist_ok=True)
    
    save_path = os.path.join(base_dir, f"{file_uuid}{ext}")
    logger.info(f"[{file_uuid}] 正在保存到: {save_path}")

    # 使用 aiofiles 异步写入文件，避免阻塞
    async with aiofiles.open(save_path, "wb") as buffer:
        while True:
            chunk = await file.read(1024 * 1024) # 1MB chunk
            if not chunk:
                break
            await buffer.write(chunk)
            
    logger.info(f"[{file_uuid}] 文件保存成功。")

    text_id = None
    photo_id = None
    task_id = None

    # 任务分发逻辑
    if task_type == "text":
        text_id = uuid()
        text_task.apply_async(args=[save_path], task_id=text_id)
    elif task_type == "photo":
        photo_id = uuid()
        photo_task.apply_async(args=[save_path], task_id=photo_id)
    elif task_type == "text_and_audio":
        text_id = uuid()
        photo_id = uuid()
        text_task.apply_async(args=[save_path], task_id=text_id)
        photo_task.apply_async(args=[save_path], task_id=photo_id)
    elif task_type == "extract_audio":
        task_id = uuid()
        extract_audio_task.apply_async(args=[save_path], task_id=task_id)
    elif task_type == "vocal_extraction":
        task_id = uuid()
        vocal_task.apply_async(args=[save_path], task_id=task_id)
    elif task_type == "stt":
        task_id = uuid()
        stt_task.apply_async(args=[save_path], task_id=task_id)
    else:
        logger.warning(f"[{file_uuid}] 无效的任务类型: {task_type}")
        raise HTTPException(status_code=400, detail="任务类型错误")
    
    logger.info(f"[{file_uuid}] Celery 任务已下发。")
    
    return {
        "status": "pending",
        "text_id": text_id,
        "photo_id": photo_id,
        "task_id": task_id,
        "message": "Tasks created"
    }

  except HTTPException as he:
    raise he
  except Exception as e:
    logger.error(f"[{file_uuid}] 错误: {str(e)}")
    raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}/status")
def get_task_status(task_id: str):
  """获取特定任务的处理状态"""
  result = AsyncResult(task_id, app=celery_app)
  return {
    "status": result.status,
    "result": result.result if result.ready() else None
  }

@app.get("/download/{task_id}")
def download_file(task_id: str):
  """下载任务处理后的文件"""
  result = AsyncResult(task_id, app=celery_app)
  
  if not result.ready():
    return {"error": "Task not completed yet"}
  
  task_result = result.result
  if not task_result or result.status != 'SUCCESS':
     return {"error": "Task failed or empty result"}

  file_path = task_result.get('output_file')
  if not file_path or not os.path.exists(file_path):
    return {"error": "File not found on server"}

  return FileResponse(
    path=file_path,
    filename=os.path.basename(file_path),
    media_type='application/octet-stream'
  )