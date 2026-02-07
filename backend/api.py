import logging
import os
import aiofiles
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from celery import uuid
from celery.result import AsyncResult
from tasks import extract_audio_task, app as celery_app 
from config import settings

# 1. 设置详细日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 修改为 async def，使用 await 方式读文件，避免同步 IO 阻塞
@app.post("/tasks/{task_type}")
async def create_task(task_type: str, file: UploadFile = File(...)):
  task_id = uuid()
  logger.info(f"[{task_id}] Received connection. Filename: {file.filename}")

  try:
    # 路径处理
    _, ext = os.path.splitext(file.filename or '')
    base_dir = settings.DEFAULT_INPUT_SAVE_DIR
    
    # 确保目录存在 (双重保险)
    os.makedirs(base_dir, exist_ok=True)
    
    save_path = os.path.join(base_dir, f"{task_id}{ext}")
    logger.info(f"[{task_id}] Saving to: {save_path}")

    # 3. 异步写入文件 (替代原来的 utils.save_upload_file)
    # 使用 aiofiles 进行真正的异步写入，避免阻塞事件循环
    async with aiofiles.open(save_path, "wb") as buffer:
        while True:
            # 每次读取 1MB
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            await buffer.write(chunk)
            
    logger.info(f"[{task_id}] File saved successfully.")

    if task_type == "extract_audio":
        logger.info(f"[{task_id}] Sending to Celery...")
        # 4. 发送任务 (这是最容易卡住的地方，如果 Redis 连不上的话)
        extract_audio_task.apply_async(args=[save_path], task_id=task_id)
        logger.info(f"[{task_id}] Celery task dispatched.")
    else:
        raise HTTPException(status_code=400, detail="任务类型错误")
    
    return {
        "status": "pending",
        "task_id": task_id,
        "message": f"task:{task_id} created"
    }

  except Exception as e:
    logger.error(f"[{task_id}] ERROR: {str(e)}")
    raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}/status")
def get_task_status(task_id: str):
  result = AsyncResult(task_id, app=celery_app)
  return {
    "status": result.status,
    "result": result.result if result.ready() else None
  }

@app.get("/download/{task_id}")
def download_file(task_id: str):
  result = AsyncResult(task_id, app=celery_app)
  if not result.ready():
    return {"error": "Task not completed yet"}
  
  # ...existing code...
  task_result = result.result
  if not task_result or result.status != 'SUCCESS':
     return {"error": "Task failed or empty"}

  file_path = task_result.get('output_file')
  if not file_path or not os.path.exists(file_path):
    return {"error": f"File not found"}

  return FileResponse(
    path=file_path,
    filename=os.path.basename(file_path),
    media_type='application/octet-stream'
  )