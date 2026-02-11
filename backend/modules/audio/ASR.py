import json
import time
import uuid
import requests
import base64
from datetime import timedelta

# 辅助函数：下载文件
def download_file(file_url):
    response = requests.get(file_url)
    if response.status_code == 200:
        return response.content  # 返回文件内容（二进制）
    else:
        raise Exception(f"下载失败，HTTP状态码: {response.status_code}")

# 辅助函数：将本地文件转换为Base64
def file_to_base64(file_path):
    try:
        with open(file_path, 'rb') as file:
            file_data = file.read()  # 读取文件内容
            base64_data = base64.b64encode(file_data).decode('utf-8')  # Base64 编码
    except Exception as e:
        raise Exception(f"读取文件失败: {e}")
    return base64_data

# recognize_task 函数
def recognize_task(file_url=None, file_path=None):
    recognize_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
    # 填入控制台获取的app id和access token
    ASR_APP_ID = '4270270778'
    ASR_Access_Token = '8fuJvmk4KDhKz3mrMCNGAYVR0uhJQBgd'
    appid = ASR_APP_ID
    token = ASR_Access_Token
    
    headers = {
        "X-Api-App-Key": appid,
        "X-Api-Access-Key": token,
        "X-Api-Resource-Id": "volc.bigasr.auc_turbo", 
        "X-Api-Request-Id": str(uuid.uuid4()),
        "X-Api-Sequence": "-1", 
    }

    # 检查是使用文件URL还是直接上传数据
    audio_data = None
    if file_url:
        audio_data = {"url": file_url}
    elif file_path:
        base64_data = file_to_base64(file_path)  # 转换文件为 Base64
        audio_data = {"data": base64_data}  # 使用Base64编码后的数据

    if not audio_data:
        raise ValueError("必须提供 file_url 或 file_path 其中之一")

    request = {
        "user": {
            "uid": appid
        },
        "audio": audio_data,
        "request": {
            "model_name": "bigmodel",
            # "enable_itn": True,
            # "enable_punc": True,
            # "enable_ddc": True,
            # "enable_speaker_info": False,

        },
    }

    response = requests.post(recognize_url, json=request, headers=headers)
    if 'X-Api-Status-Code' in response.headers:
        print(f'recognize task response header X-Api-Status-Code: {response.headers["X-Api-Status-Code"]}')
        print(f'recognize task response header X-Api-Message: {response.headers["X-Api-Message"]}')
        print(time.asctime() + " recognize task response header X-Tt-Logid: {}".format(response.headers["X-Tt-Logid"]))
    else:
        print(f'recognize task failed and the response headers are:: {response.headers}\n')
        exit(1)
    return response

# recognizeMode 不变
def recognizeMode(file_url=None, file_path=None,output_path=None):
    start_time = time.time()
    print(time.asctime() + " START!")
    recognize_response = recognize_task(file_url=file_url, file_path=file_path)
    code = recognize_response.headers['X-Api-Status-Code']
    logid = recognize_response.headers['X-Tt-Logid']
    utterances=recognize_response.json().get("result", dict).get("utterances",[])
    if code == '20000000':  # task finished
        with open(output_path, mode='w', encoding='utf-8') as f:
            for utterance in utterances:
                start=str(timedelta(milliseconds=utterance.get("start_time",0)))[:-4]
                end=str(timedelta(milliseconds=utterance.get("end_time",0)))[:-4]
                text=utterance.get("text","")
                f.write(f"[{start} - {end}] {text}\n")
        print(time.asctime() + " SUCCESS! \n")
        print(f"程序运行耗时: {time.time() - start_time:.6f} 秒")
    elif code != '20000001' and code != '20000002':  # task failed
        print(time.asctime() + " FAILED! code: {}, logid: {}".format(code, logid))
        print("headers:")
        raise Exception("使用模型转文字时发生错误，错误码：{}，logid：{}".format(code, logid))
        # print(query_response.content)

def main(): 
    # 示例：通过 URL 或 文件路径选择传入参数
    file_url = "https://example.mp3"
    file_path = "D:/User/Document/NJU Works/My Project/fast-vid-processor/backend/data/processed/separate_audiotrack/be520e39-9cdd-4e15-a923-1ac9f35b530b_audio_0.mp3"  # 如果你有本地文件，可以选择这个 
    recognizeMode(file_path=file_path)  # 或者 recognizeMode(file_path=file_path)
    # recognizeMode(file_path=file_path)  # 或者 recognizeMode(file_path=file_path)


def ASR(file_url=None, input_path=None,output_path=None):
    recognizeMode(file_url=file_url, file_path=input_path,output_path=output_path)
    return output_path




if __name__ == '__main__': 
    main()
    