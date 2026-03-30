import os
import uuid
from flask import Flask, render_template, request, send_file
import edge_tts
import pysrt
import asyncio
from pydub import AudioSegment

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

async def generate_segment(text, voice):
    """生成单段音频并返回 AudioSegment 对象"""
    communicate = edge_tts.Communicate(text, voice)
    # 将音频存入临时文件
    temp_file = f"temp_{uuid.uuid4()}.mp3"
    await communicate.save(temp_file)
    audio = AudioSegment.from_mp3(temp_file)
    os.remove(temp_file)
    return audio

@app.route('/convert', methods=['POST'])
def convert():
    file = request.files['file']
    voice = request.form.get('voice', 'zh-CN-XiaoxiaoNeural')
    
    unique_id = str(uuid.uuid4())
    srt_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}.srt")
    output_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}.mp3")
    file.save(srt_path)
    
    subs = pysrt.open(srt_path)
    
    # 初始化一个空白音频
    final_audio = AudioSegment.empty()
    last_end_time = 0

    # 循环处理每一段
    for sub in subs:
        # 计算当前字幕开始时间（毫秒）
        start_ms = sub.start.ordinal
        # 插入静音，确保时间轴对齐
        silence_duration = start_ms - last_end_time
        if silence_duration > 0:
            final_audio += AudioSegment.silent(duration=silence_duration)
            
        # 生成当前段语音
        segment_audio = asyncio.run(generate_segment(sub.text, voice))
        final_audio += segment_audio
        
        last_end_time = sub.end.ordinal

    final_audio.export(output_path, format="mp3")
    return send_file(output_path, as_attachment=True)
if __name__ == '__main__':
    # 必须指定 host='0.0.0.0'，否则容器外无法访问
    app.run(host='0.0.0.0', port=5000, debug=True)

