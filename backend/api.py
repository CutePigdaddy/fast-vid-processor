from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from celery import uuid, Task
from celery.result import AsyncResult
from tasks import extract_audio_task, app as celery_app  # type: ignore
from utils import save_upload_file
from config import settings
import os
app = FastAPI()

# 配置 CORS，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 这里的 "*" 可以改为你的前端地址 "http://localhost:3000"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

extract_audio_task: Task = extract_audio_task 

@app.post("/tasks/{task_type}")
def create_task(task_type: str, file: UploadFile=File(...)):
  """
  创建一个新任务的API端点。

  :param task_type: 任务的类型,包含 "extract_audio"。
  """
  #生成taskid
  task_id = uuid()

  #保存文件
  _,ext = os.path.splitext(file.filename or '')
  base_dir = settings.DEFAULT_INPUT_SAVE_DIR
  save_path = os.path.join(base_dir,f"{task_id}{ext}")
  save_upload_file(file,save_path)

  if task_type=="extract_audio":
    extract_audio_task.apply_async(args=[save_path], task_id=task_id) 
  else:
    raise Exception("任务类型错误")
  
  return {
    "status": "pending",
    "task_id": task_id,
    "message": f"task:{task_id} created"
  }

@app.get("/tasks/{task_id}/status")
def get_task_status(task_id: str):
  """
  获取特定任务id的处理状态
  
  :param task_id: 前端返回给用户的任务id
  :type task_id: str
  """
  result = AsyncResult(task_id, app=celery_app)

  return {
    "status": result.status,
    "result": result.result if result.ready() else None
  }

@app.get("/download/{task_id}")
def download_file(task_id: str):
  """
  下载任务处理后的文件
  
  :param task_id: 任务ID
  :return: 文件响应
  """
  result = AsyncResult(task_id, app=celery_app)
  
  if not result.ready():
    return {"error": "Task not completed yet"}
  
  if result.status != 'SUCCESS':
    return {"error": "Task failed"}
  
  task_result = result.result
  if not task_result:
    return {"error": "No result data"}
  
  file_path = task_result['output_file']
  
  if not os.path.exists(file_path):
    return {"error": f"File not found at: {file_path}"}
  
  filename = os.path.basename(file_path)
  return FileResponse(
    path=file_path,
    filename=filename,
    media_type='application/octet-stream'
  )