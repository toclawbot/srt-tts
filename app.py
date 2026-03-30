import os
import uuid
from flask import Flask, render_template, request, send_file
import edge_tts
import pysrt
import asyncio

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

async def generate_audio(text, output_path, voice):
    # 限制字符数防止过长报错
    text = text[:200]
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return "没有文件", 400
    
    file = request.files['file']
    voice = request.form.get('voice', 'zh-CN-XiaoxiaoNeural')
    
    # 使用唯一文件名防止覆盖
    unique_id = str(uuid.uuid4())
    filepath = os.path.join(UPLOAD_FOLDER, f"{unique_id}.srt")
    output_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}.mp3")
    
    file.save(filepath)
    
    # 解析 SRT
    subs = pysrt.open(filepath)
    if not subs:
        return "SRT为空", 400
        
    # 运行异步任务
    asyncio.run(generate_audio(subs[0].text, output_path, voice))
    
    return send_file(output_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
