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
    file_hash: str,
    file: UploadFile = File(...),
    extract_audio: bool = Form(False),
    transcribe: bool = Form(False),
    ai_summarize: bool = Form(False),
    extract_keyframes: bool = Form(False)

    ):
    """
    创建处理任务。

    :param file_hash: 文件的 SHA-256 哈希值，用于唯一标识文件。
    :param file: 上传的视频文件。
    :param extract_audio: 是否提取音轨。
    :param transcribe: 是否进行语音转文字。
    :param ai_summarize: 是否进行AI摘要。
    :param extract_keyframes: 是否提取关键帧。
    :return: 任务创建结果。 
    """

    
    if not file_hash:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    logger.info(f"[{file_hash}] 收到上传请求: filename={file.filename}, extract_audio={extract_audio}, transcribe={transcribe}, ai_summarize={ai_summarize}, extract_keyframes={extract_keyframes}")

    try:
        # 创建目录结构
        settings.ensure_hash_dirs(file_hash)
        if not file.filename:
            raise HTTPException(status_code=400, detail="上传文件不能为空")
        _,ext = os.path.splitext(file.filename)
        # 保存源文件到 data/<HASH>/source/<HASH><ext>
        source_dir = settings.get_source_dir(settings.DATA_DIR, file_hash)
        save_path = os.path.join(source_dir, f"{file_hash}{ext}")
        
        logger.info(f"[{file_hash}] 正在保存到: {save_path}")
        await save_upload_file(file, save_path)
        logger.info(f"[{file_hash}] 文件保存成功")
        
        # 写入/更新数据库记录
        
        # 下发 Celery 任务
        workflow_tasks = []
        response_tasks = []
        if extract_audio:
          audio_task_id = uuid()
          workflow_tasks.append(extract_audio_task.si(file_hash).set(task_id=audio_task_id))
          response_tasks.append({"task_name": "extract_audio", "task_id": audio_task_id})
        if transcribe:
          if not extract_audio:
              raise HTTPException(status_code=400, detail="语音转文字需要先提取音轨")
          asr_task_id = uuid()
          workflow_tasks.append(asr_task.si(file_hash).set(task_id=asr_task_id))
          response_tasks.append({"task_name": "asr", "task_id": asr_task_id})
        if ai_summarize:
          if not transcribe:
              raise HTTPException(status_code=400, detail="AI摘要需要先进行语音转文字")
          ai_summarize_task_id = uuid()
          workflow_tasks.append(ai_summarize_task.si(file_hash).set(task_id=ai_summarize_task_id))
          response_tasks.append({"task_name": "ai_summarize", "task_id": ai_summarize_task_id})
        if extract_keyframes:
          extract_keyframes_task_id = uuid()
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


@app.get("/files/{file_hash}/status")
def get_file_status(file_hash: str):
    """
    查询文件处理状态。
    """
    #数据库轮询查询taskid
    


@app.get("/files/{file_hash}/download/{file_type}")
def download_file(file_hash: str, file_type: str):
    """
    下载处理后的文件。
    file_type: text / track / vocal / source / keyframes
    """
    # 检查文件是否存在于数据库
    
    # 根据 file_type 确定路径
    type_map = {
        "text": (settings.get_text_dir, f"{file_hash}.txt"),
        "track": (settings.get_track_dir, f"{file_hash}.mp3"),
        "vocal": (settings.get_vocal_dir, f"{file_hash}.mp3"),
        "keyframes": (settings.get_keyframes_dir, "")
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
    #数据库查询状态
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