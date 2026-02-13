# Fast Video Processor (FastVidProcessor)

一个全栈式的高效音视频处理平台，旨在实现视频内容的深度分析与转化。该项目集成了自动语音转录（ASR）、人声分离、AI 摘要生成、关键帧提取以及 OCR 识别等功能，并提供了现代化的 Web 界面进行交互。

## 🚀 核心功能

*   **全栈架构**：基于 FastAPI (后端) + Next.js (前端) + Celery (异步任务) 的现代化架构。
*   **高效转录**：利用 `faster-whisper` 实现高性能的语音识别，支持长音频精准转写。
*   **智能音频处理**：
    *   **人声分离**：自动分离背景音乐与人声，提取纯净语音。
    *   **音轨提取**：支持从视频中快速提取音频。
*   **视频内容分析**：
    *   **关键帧提取**：智能提取视频关键画面。
    *   **OCR 识别**：识别视频画面中的文字信息 (开发中)。
*   **AI 辅助**：集成 AI 模块，对转录文本进行摘要生成和关键信息提取。
*   **多源支持**：支持本地上传视频，以及在线视频流（如 Bilibili）的处理。
*   **容器化部署**：提供完整的 Docker 支持，一键启动所有服务。

## 🏗️ 系统架构

*   **Frontend**: Next.js (React) - 提供用户交互界面。
*   **Backend**: FastAPI - 处理 API 请求，管理任务调度。
*   **Worker**: Celery - 异步处理耗时的视频/音频处理任务。
*   **Broker**: Redis - 消息队列与结果存储。
*   **Core Modules**: 包含音频处理 (`modules/audio`)、视觉处理 (`modules/vision`)、在线流媒体 (`modules/online`) 等核心算法模块。

## 📦 快速部署 (Docker) - 推荐

使用 Docker Compose 可以一键启动整个项目，无需手动配置复杂的环境依赖（如 FFmpeg, CUDA, Redis 等）。

### 前置要求
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) 或 Docker Engine (Linux)

### 启动步骤

1.  **克隆仓库**
    ```bash
    git clone https://github.com/YourUsername/fast-vid-processor.git
    cd fast-vid-processor
    ```

2.  **构建并启动服务**
    ```bash
    docker-compose up --build
    ```
    *首次启动需要下载模型和构建镜像，可能需要一些时间。*

3.  **访问应用**
    *   **Web 前端**: [http://localhost:3000](http://localhost:3000)
    *   **后端 API 文档**: [http://localhost:8080/docs](http://localhost:8080/docs)
    *   **Redis**: 运行在端口 `6379`

## 🛠️ 本地开发指南

如果你希望在本地分别运行前后端进行开发调试：

### 1. 后端 (Backend)

**环境要求**: Python 3.10+, Redis, FFmpeg

```bash
cd backend

# 1. 创建虚拟环境 (可选)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate # Windows

# 2. 安装依赖 (PyTorch 请根据官网指引安装对应 CUDA 版本)
pip install -r requirements.txt

# 3. 启动 Redis (必须)
# 请确保通过 Docker 或本地安装启动了 Redis 服务

# 4. 启动 Celery Worker (处理异步任务)
celery -A tasks worker --loglevel=info

# 5. 启动 FastAPI 服务
python -m uvicorn api:app --reload --port 8000
```

### 2. 前端 (Frontend)

**环境要求**: Node.js 18+

```bash
cd frontend

# 1. 安装依赖
npm install
# 或 yarn install / pnpm install

# 2. 启动开发服务器
npm run dev
```
访问 [http://localhost:3000](http://localhost:3000) 查看前端页面。

## 📂 项目结构

```
fast-vid-processor/
├── backend/                # 后端代码 (FastAPI)
│   ├── api.py              # API 入口
│   ├── tasks.py            # Celery 任务定义
│   ├── modules/            # 核心处理逻辑 (Audio, Vision, AI, etc.)
│   └── Dockerfile
├── frontend/               # 前端代码 (Next.js)
│   ├── app/                # 页面逻辑
│   └── Dockerfile
├── data/                   # 数据存储目录 (Docker 挂载卷)
├── docker-compose.yml      # Docker 编排文件
└── README.md
```

## 📝 API 接口说明

后端服务启动后，可访问 `/docs` 查看交互式 Swagger 文档。主要接口包括：

*   `POST /tasks/{file_hash}`: 上传文件并创建处理任务（支持选择是否提取音频、转录、AI摘要等）。
*   `GET /tasks/{task_id}`: 查询任务处理状态及进度。
*   `GET /results/{task_id}/download`: 下载处理结果。

## 📄 License

[MIT License](LICENSE)

