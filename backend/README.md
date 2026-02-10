# Backend API (FastAPI)

面向前端的接口说明，便于快速对接上传、任务状态查询和结果下载。

## Base URL

- 本地开发: `http://localhost:8000`
- 生产环境: 以部署地址为准

## 通用说明

- 所有返回均为 JSON (文件下载接口除外)。
- 任务为异步执行，请通过状态接口轮询。
- `file_hash` 用于标识同一文件的处理任务，建议使用文件内容的 MD5。
- `task_id` 由后端生成 (UUID)，用于查询单个任务状态或下载结果。

## 1) 创建任务 (上传文件)

**POST** `/tasks/{file_hash}`

- `Content-Type`: `multipart/form-data`

**Path 参数**
- `file_hash`: 文件哈希

**Form 参数**
- `file`: 上传的视频文件
- `file_hash`: 文件哈希 (需与 Path 参数保持一致)
- `file_origin_name`: 原始文件名
- `extract_audio`: 是否提取音轨 (bool)
- `transcribe`: 是否语音转文字 (bool)
- `ai_summarize`: 是否 AI 摘要 (bool)
- `extract_keyframes`: 是否提取关键帧 (bool)

**响应**
```json
{
  "status": "processing",
  "tasks": [
    {"task_name": "extract_audio", "task_id": "..."},
    {"task_name": "asr", "task_id": "..."},
    {"task_name": "ai_summarize", "task_id": "..."}
  ]
}
```

**常见错误**
- `400` 文件名为空
- `400` 语音转文字需要先提取音轨
- `400` AI 摘要需要先进行语音转文字

**示例 (curl)**
```bash
curl -X POST "http://localhost:8000/tasks/your_file_hash" \
  -F "file=@/path/to/video.mp4" \
  -F "file_hash=your_file_hash" \
  -F "file_origin_name=video.mp4" \
  -F "extract_audio=true" \
  -F "transcribe=true" \
  -F "ai_summarize=true" \
  -F "extract_keyframes=false"
```

## 2) 查询文件处理状态 (聚合)

**GET** `/status/{file_hash}`

**响应示例**
```json
{
  "extract_audio": {
    "status": "completed",
    "result_path": "/path/to/audio.wav",
    "completed_at": "2026-02-10T10:30:00",
    "task_id": "extract_audio_xxx"
  },
  "transcribe": {
    "status": "completed",
    "result_path": "/path/to/transcript.txt",
    "completed_at": "2026-02-10T10:35:00",
    "task_id": "transcribe_xxx"
  }
}
```

**常见错误**
- `404` 文件不存在

## 3) 查询单个任务状态

**GET** `/tasks/{task_id}/status`

**响应示例**
```json
{
  "task_id": "...",
  "file_hash": "...",
  "task_type": "transcribe",
  "status": "pending/running/success/failed",
  "created_at": "2026-02-10T10:30:00",
  "started_at": "2026-02-10T10:31:00",
  "completed_at": "2026-02-10T10:35:00",
  "result_path": "/path/to/result",
  "error_message": "错误信息(如果有)"
}
```

**常见错误**
- `404` 任务不存在

## 4) 查询文件的所有任务记录

**GET** `/tasks/{file_hash}/all`

**响应**
```json
[
  {
    "task_id": "...",
    "task_type": "extract_audio",
    "status": "success",
    "result_path": "/path/to/audio.wav"
  }
]
```

## 5) 下载任务结果文件

**GET** `/files/{task_id}`

- 仅当任务状态为 `success` 时可下载。

**常见错误**
- `404` 任务不存在
- `400` 任务未完成/未成功
- `404` 结果文件不存在

## 6) 获取转写文本内容

**GET** `/files/{file_hash}/text`

**响应**
```json
{
  "file_hash": "...",
  "text_content": "..."
}
```

**常见错误**
- `400` 转写任务未完成
- `404` 文本文件不存在

## 前端推荐调用流程

1. `POST /tasks/{file_hash}` 上传并创建任务
2. 轮询：
   - `GET /tasks/{task_id}/status` (单任务)
   - 或 `GET /status/{file_hash}` (聚合状态)
3. 任务成功后：
   - `GET /files/{task_id}` 下载结果文件
   - 或 `GET /files/{file_hash}/text` 获取转写文本

## 说明

- `file_hash` 既作为路径参数又在表单中传入，建议保持一致。
- 异步任务依赖 Celery，任务执行时间取决于文件大小与模型调用耗时。
