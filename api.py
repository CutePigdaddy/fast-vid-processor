from fastapi import FastAPI, UploadFile, File
from celery import uuid, Task
from celery.result import AsyncResult
from tasks import extract_audio_task #type: ignore
from utils import save_upload_file
from config import settings
import os
app = FastAPI()

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
  save_path = os.path.join(base_dir,f"{task_id}.{ext}")
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
  result = AsyncResult(task_id)

  return {
    "status": result.status,
    "result": result.result if result.ready() else None
  }