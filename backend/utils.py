import os
import zipfile
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


def zip_keyframes(output_dir: str, file_hash: str) -> str:
  """Package keyframes into a zip file stored alongside the directory."""
  zip_path = os.path.join(output_dir, f"{file_hash}.zip")
  with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
    for root, _, files in os.walk(output_dir):
      for filename in files:
        if filename == os.path.basename(zip_path):
          continue
        file_path = os.path.join(root, filename)
        arcname = os.path.relpath(file_path, output_dir)
        zipf.write(file_path, arcname)
  return zip_path