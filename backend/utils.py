import os
import shutil
import aiofiles
from fastapi import UploadFile

async def save_upload_file(upload_file: UploadFile, destination_path: str):
  os.makedirs(os.path.dirname(destination_path),exist_ok=True)

  # 使用 aiofiles 异步写入文件，避免阻塞
  async with aiofiles.open(destination_path, "wb") as buffer:
    while True:
      chunk = await upload_file.read(1024 * 1024) # 1MB chunk
      if not chunk:
        break
      await buffer.write(chunk)