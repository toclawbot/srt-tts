import os
from flask import Flask, render_template, request, send_file
import edge_tts
import pysrt
import asyncio

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

async def generate_audio(text, output_path):
    # 限制每段请求字符数，防止 edge-tts 报错
    text = text[:200]
    communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
    await communicate.save(output_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    file = request.files['file']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    
    # 这里简化：仅处理第一个字幕段作为测试
    subs = pysrt.open(filepath)
    output_path = os.path.join(UPLOAD_FOLDER, "output.mp3")
    
    # 同步运行异步任务
    asyncio.run(generate_audio(subs[0].text, output_path))
    
    return send_file(output_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
