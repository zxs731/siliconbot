import pyaudio  
import wave  
import numpy as np  
import time
import requests  
import json
from dotenv import load_dotenv
import os  
  
# 加载已有的 .env 文件（如果存在）  
load_dotenv("./1.env")    
# 配置  
FORMAT = pyaudio.paInt16  # 音频格式  
CHANNELS = 1               # 单声道  
RATE = 44100               # 采样率  
CHUNK = 1024               # 每次读取的音频帧数  
THRESHOLD = 200            # 音量阈值  
RECORD_SECONDS = 20        # 最大录音时间  
SILENCE_DURATION = 1      # 静音持续时间（秒） 
sk_key=os.getenv('key') 
  
def get_volume(data):  
    """计算音量"""  
    return np.frombuffer(data, dtype=np.int16).astype(np.float32).mean()  
  
def record_audio():  
    """录制音频并保存为 WAV 文件"""  
    audio = pyaudio.PyAudio()  
      
    # 开始流  
    stream = audio.open(format=FORMAT, channels=CHANNELS,  
                        rate=RATE, input=True,  
                        frames_per_buffer=CHUNK)  
      
    print("检测话音音量...")  
  
    frames = []  
    recording = False  
    silence_start_time = None  # 用于记录静音开始时间  
    start_time = time.time()    # 记录开始时间  
  
    while True:  
        # 读取音频数据  
        data = stream.read(CHUNK)  
        volume = get_volume(data)  
          
        if volume > THRESHOLD and not recording:  
            print("持续聆听中...")  
            recording = True  
            start_time = time.time()  # 记录开始时间  
            silence_start_time = None  # 重置静音计时器  
          
        if recording:  
            frames.append(data)  
            #print(f"录音中... 音量: {volume}")  
            print(f".",end="")  
  
            # 检查录音时间  
            if time.time() - start_time > RECORD_SECONDS:  
                print("达到最大录音时间，停止录音")  
                break  
  
            # 检查静音  
            if volume < THRESHOLD:  
                if silence_start_time is None:  
                    silence_start_time = time.time()  # 记录静音开始时间  
                elif time.time() - silence_start_time > SILENCE_DURATION:  
                    print("检测到静音超过 1 秒，停止录音")  
                    break  
            else:  
                silence_start_time = None  # 重置静音计时器  
  
    # 停止流  
    stream.stop_stream()  
    stream.close()  
    audio.terminate()  
  
    # 保存录音  
    if frames:  
        with wave.open("output.wav", 'wb') as wf:  
            wf.setnchannels(CHANNELS)  
            wf.setsampwidth(audio.get_sample_size(FORMAT))  
            wf.setframerate(RATE)  
            wf.writeframes(b''.join(frames))  
        print("录音已保存为 output.wav")  
    else:  
        print("没有录音数据")  


def transcribe_audio(file_path):  
    """将音频文件发送到 API 并返回转录文本"""  
    url = "https://api.siliconflow.cn/v1/audio/transcriptions"

    payload = {'model': 'FunAudioLLM/SenseVoiceSmall'}
    f=open('output.wav','rb')
    files=[
      ('file',('1.wav',f,'audio/wav'))
    ]
    headers = {
      'Authorization': f"Bearer {sk_key}"
    }
    try:  
        response = requests.request("POST", url, headers=headers, data=payload, files=files)
        response.raise_for_status()  # 检查请求是否成功  
  
        # 解析 JSON 响应  
        json_response = response.json()  
        return json_response.get('text', '').strip()  # 返回 text 字段的值，如果没有则返回空字符串  
  
    except requests.exceptions.RequestException as e:  
        print(f"请求失败: {e}")  
        return None  
    except Exception as e:  
        print(f"发生错误: {e}")  
        return None  
    finally:  
        f.close()  # 确保文件在结束时关闭  

def text2speech(text):
    # API 请求
    url = "https://api.siliconflow.cn/v1/audio/speech"
    
    payload = {
        "model": "fishaudio/fish-speech-1.5",
        "voice": "fishaudio/fish-speech-1.5:anna",
        "input": text,
        "response_format": "pcm"  # 直接请求 PCM 格式
    }
    
    headers = {
        "Authorization": f"Bearer {sk_key}"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    # 检查请求是否成功
    if response.status_code == 200:
        # 获取 PCM 数据
        pcm_data = response.content
    
        # 初始化 PyAudio
        p = pyaudio.PyAudio()
    
        # 打开音频流
        stream = p.open(format=pyaudio.paInt16,  # PCM 数据通常为 16 位
                        channels=1,             # 单声道
                        rate=44100,             # 采样率（根据 API 返回的采样率调整）
                        output=True)            # 输出流
    
        # 播放 PCM 数据
        print(f"{text}")
        stream.write(pcm_data)
        #print("播放完成！")
    
        # 关闭流和 PyAudio
        stream.stop_stream()
        stream.close()
        p.terminate()
    else:
        print("没有需要说的！")

messages=[]
def generate():  
    global messages  
    url = "https://api.siliconflow.cn/v1/chat/completions"  
      
    payload = {  
        "model": "deepseek-ai/DeepSeek-V3",  
        "messages": messages[-20:],  
        "stream": True,  # 设置为 True 以启用流式返回  
        "max_tokens": 200,  
        "stop": ["null"],  
        "temperature": 0.7,  
        "top_p": 0.7,  
        "top_k": 50,  
        "frequency_penalty": 0.5,  
        "n": 1,  
        "response_format": {"type": "text"}  
    }  
      
    headers = {  
        "Authorization": f"Bearer {sk_key}",  
        "Content-Type": "application/json"  
    }  
      
    response = requests.post(url, json=payload, headers=headers, stream=True)  
  
    if response.status_code == 200:  
        result_buffer = ""  
        result_all=""
        print("AI:")
        for line in response.iter_lines():  
            if line:  
                # 解析每一行的内容  
                try:  
                    json_line = line.decode('utf-8')  
                    
                    if json_line!="data: [DONE]":
                        json_line=json_line.replace("data: {","{")
                        message = json.loads(json_line)["choices"][0]["delta"]["content"]  
                        result_buffer += message 
                        result_all+=message
                    else:
                        message=""
                      
                    # 检测句子结束并进行朗读  
                    if message.endswith(('!', '?','。','！','？','\n\n')): 
                        #print(result_buffer.strip())
                        text2speech(result_buffer.strip().replace("*","").replace("-"," "))  
                        result_buffer = ""  # 清空缓冲区  
                except Exception as e:  
                    print(f"解析响应失败: {e}")  
        # 处理剩余的内容  
        if result_buffer:  
            text2speech(result_buffer.strip().replace("*","").replace("#",""))  
  
        messages.append({"role": "assistant", "content": result_all.strip()})  
    else:  
        #print(f"Generate请求失败，状态码：{response.status_code}")  
        print(f"...")  
        return None  
        
if __name__ == "__main__": 
    text2speech("很高兴为您服务，我在听请讲！")
    while True:
        record_audio()
        question = transcribe_audio("output.wav")
        print(f"你: {question}")
        if question=="退出。":
            break
        if question is None or question=="":
            text2speech("我没听清，您可以大点声吗？")
            continue
        messages=messages+[{"role":"user","content":question}]
        answer = generate()
        