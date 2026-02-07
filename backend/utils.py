import os
import shutil
from fastapi import UploadFile

def save_upload_file(upload_file: UploadFile, destination_path: str):
  os.makedirs(os.path.dirname(destination_path),exist_ok=True)

  #使用shutil流式拷贝
  try:
    with open(destination_path,'wb') as buffer:
      shutil.copyfileobj(upload_file.file, buffer)
  finally:
    upload_file.file.close()
  
  return os.path.abspath(destination_path)