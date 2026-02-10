import logging
import os
from utils import save_upload_file
from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from celery import uuid, Task, chain
from celery.result import AsyncResult
from tasks import extract_audio_task, asr_task, ai_summarize_task, extract_keyframes_task, app as celery_app #type: ignore
from config import settings
from modules.database import db

extract_audio_task: Task = extract_audio_task
asr_task: Task = asr_task
ai_summarize_task: Task = ai_summarize_task
extract_keyframes_task: Task = extract_keyframes_task
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


@app.post("/tasks/{file_hash}")
async def create_task(
    file: UploadFile = File(...),
    file_hash: str = Form(...),
    file_origin_name: str = Form(...),
    extract_audio: bool = Form(False),
    transcribe: bool = Form(False),
    ai_summarize: bool = Form(False),
    extract_keyframes: bool = Form(False)

    ):
    """
    创建处理任务。

    :param file: 上传的视频文件。
    :param file_hash: 文件的唯一标识（MD5 哈希值）。
    :param file_origin_name: 文件的原始名称。
    :param extract_audio: 是否提取音轨。
    :param transcribe: 是否进行语音转文字。
    :param ai_summarize: 是否进行AI摘要。
    :param extract_keyframes: 是否提取关键帧。
    :return: 任务创建结果。 
    """

    
    if not file_hash:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    logger.info(f"[{file_hash}] 收到上传请求: filename={file_origin_name}, extract_audio={extract_audio}, transcribe={transcribe}, ai_summarize={ai_summarize}, extract_keyframes={extract_keyframes}")
    try:
        # 创建目录结构
        settings.ensure_hash_dirs(file_hash)
        if not file_origin_name:
            raise HTTPException(status_code=400, detail="上传文件名不能为空")
        _,ext = os.path.splitext(file_origin_name)
        # 保存源文件到 data/<HASH>/source/<HASH><ext>
        source_dir = settings.get_source_dir(settings.DATA_DIR, file_hash)
        save_path = os.path.join(source_dir, f"{file_origin_name}{ext}")
        if os.path.exists(save_path):
            logger.warning(f"[{file_hash}] 文件已存在: {save_path}")
        else:
            logger.info(f"[{file_hash}] 正在保存到: {save_path}")
            await save_upload_file(file, save_path)
            logger.info(f"[{file_hash}] 文件保存成功")
        
        # 写入/更新数据库记录
        db.increment_upload_count(file_hash)
        if db.check_file_exists(file_hash):
            logger.info(f"[{file_hash}] 数据库记录已存在，跳过保存")
        else:
            logger.info(f"[{file_hash}] 数据库记录不存在，更新数据库")
            db.save_file_info(file_hash, file_origin_name, save_path)
        
        # 下发 Celery 任务
        workflow_tasks = []
        response_tasks = []
        if extract_audio:
            if db.has_operation_completed(file_hash, "extract_audio"):
                logger.info(f"[{file_hash}] 音轨已提取，跳过任务")
            audio_task_id = uuid()
            db.create_task(audio_task_id, file_hash, "extract_audio")
            db.update_processed_operation(file_hash, "extract_audio", "pending", task_id=audio_task_id)
            workflow_tasks.append(extract_audio_task.si(file_hash).set(task_id=audio_task_id))
            response_tasks.append({"task_name": "extract_audio", "task_id": audio_task_id})
        if transcribe:
            if not extract_audio and not db.has_operation_completed(file_hash, "extract_audio"):
                 raise HTTPException(status_code=400, detail="语音转文字需要先提取音轨")
            if db.has_operation_completed(file_hash, "transcribe"):
                logger.info(f"[{file_hash}] 转写已完成，跳过任务")
            asr_task_id = uuid()
            db.create_task(asr_task_id, file_hash, "transcribe")
            db.update_processed_operation(file_hash, "transcribe", "pending", task_id=asr_task_id)
            workflow_tasks.append(asr_task.si(file_hash).set(task_id=asr_task_id))
            response_tasks.append({"task_name": "asr", "task_id": asr_task_id})
        if ai_summarize:
            if not transcribe and not db.has_operation_completed(file_hash, "transcribe"):
                  raise HTTPException(status_code=400, detail="AI摘要需要先进行语音转文字")
            ai_summarize_task_id = uuid()
            db.create_task(ai_summarize_task_id, file_hash, "ai_summarize")
            db.update_processed_operation(file_hash, "ai_summarize", "pending", task_id=ai_summarize_task_id)
            workflow_tasks.append(ai_summarize_task.si(file_hash).set(task_id=ai_summarize_task_id))
            response_tasks.append({"task_name": "ai_summarize", "task_id": ai_summarize_task_id})
        if extract_keyframes:
            extract_keyframes_task_id = uuid()
            db.create_task(extract_keyframes_task_id, file_hash, "extract_keyframes")
            db.update_processed_operation(file_hash, "extract_keyframes", "pending", task_id=extract_keyframes_task_id)
            workflow_tasks.append(extract_keyframes_task.si(file_hash).set(task_id=extract_keyframes_task_id))
            response_tasks.append({"task_name": "extract_keyframes", "task_id": extract_keyframes_task_id})
        #数据库记录taskid
        workflow = chain(*workflow_tasks)
        workflow.apply_async()
        return {
            "status": "processing",
            "tasks": response_tasks
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[{file_hash}] 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{file_hash}")
def get_status(file_hash: str):
    """
    获取文件处理状态。
    返回格式示例：
    {
      "extract_audio": {
        "status": "completed",
        "result_path": "/path/to/audio.wav",
        "completed_at": "2026-02-10T10:30:00"
      },
      "transcribe": {
        "status": "completed",
        "result_path": "/path/to/transcript.txt",
        "completed_at": "2026-02-10T10:35:00"
      },
      "ai_summarize": {
        "status": "completed",
        "result_path": "/path/to/summary.md",
        "completed_at": "2026-02-10T10:40:00"
      }
    }

    :param file_hash: 文件的唯一标识（MD5 哈希值）。
    :return: 文件处理状态。
    
    """
    try:
        status = db.get_processed_operations(file_hash)
        if not status:
            raise HTTPException(status_code=404, detail="文件不存在")
        return status
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[{file_hash}] 获取状态错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}/status")
def get_task_status(task_id: str):
    """
    获取单个任务状态。
    返回示例:
    {
      "task_id": "...",
      "file_hash": "...",
      "task_type": "...",
      "status": "pending/running/success/failed",
      "created_at": "2026-02-10T10:30:00",
      "started_at": "2026-02-10T10:31:00",
      "completed_at": "2026-02-10T10:35:00",
      "result_path": "/path/to/result",
      "error_message": "错误信息（如果有）"
    }

    :param task_id: 任务ID（UUID）。
    :return: 任务状态。
    """
    try:
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return task
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[{task_id}] 获取任务状态错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{file_hash}/all")
def get_file_all_tasks(file_hash: str):
    """
    获取文件的所有任务状态（包括未完成的任务）。
    返回示例
    [
        {
            "task_id": "...",
            "file_hash": "...",
            "task_type": "...",
            "status": "pending/running/success/failed",
            "created_at": "2026-02-10 ...",
            "started_at": "...",
            "completed_at": "...",
            "result_path": "...",
            "error_message": "..."
        },
        ...
    ]
    
    :param file_hash: 文件的唯一标识（MD5 哈希值）。
    :return: 文件的所有任务状态列表。
    """
    return db.get_file_tasks(file_hash)

@app.get("/files/{task_id}")
def download_file(task_id: str):
    """
    下载处理后的文件.

    :param task_id: 任务ID（UUID）。
    """
    task = db.get_task(task_id) 
    #检查任务是否存在
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task_status = task['status']
    #检查任务是否成功完成
    if task_status != "success":
        raise HTTPException(status_code=400, detail=f"任务未完成/未成功，当前状态: {task_status}")
    #检查结果文件是否存在
    file_path = task['result_path']
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
    #数据库查询状态
    status = db.has_operation_completed(file_hash, "transcribe")
    if not status:
        raise HTTPException(status_code=400, detail="转写任务未完成")
    text_path = os.path.join(text_dir, f"{file_hash}.txt")
    
    if not os.path.exists(text_path):
        raise HTTPException(status_code=404, detail="文本文件不存在")
    
    with open(text_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {
        "file_hash": file_hash,
        "text_content": content
    }