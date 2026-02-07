# 使用 Python 3.12 轻量版
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
# 1. ffmpeg/libsm6/libxext6: 视频处理库 (opencv 等需要)
# 2. gcc/build-essential/python3-dev: 编译 Python C 扩展所必需的工具 (解决 diffq/bitpack 报错)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    gcc \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY . .

# 创建数据目录挂载点
RUN mkdir -p /app/data/uploads

# 暴露端口 (仅用于 API 服务，Worker 不需要暴露端口)
EXPOSE 8000

# 默认启动命令 (会被 docker-compose 覆盖)
# 使用 python -m uvicorn 替代直接调用 uvicorn，解决找不到可执行文件的问题
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]