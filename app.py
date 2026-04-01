import os
import uuid
import shutil
from flask import Flask, render_template, request, send_file, jsonify
import edge_tts
import pysrt
import asyncio
from pydub import AudioSegment

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
TEMP_FOLDER = 'temp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# 存储转换进度
conversion_progress = {}


def cleanup_temp_files():
    """清理临时文件"""
    try:
        for filename in os.listdir(TEMP_FOLDER):
            file_path = os.path.join(TEMP_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except Exception as e:
        print(f"清理临时文件时出错: {e}")


@app.route('/')
def index():
    return render_template('index.html')


async def generate_segment(text, voice, rate='+0%'):
    """生成单段音频并返回 AudioSegment 对象

    Args:
        text: 要转换的文本
        voice: 语音类型
        rate: 语速，默认 '+0%'，可以是 '+50%' (加速) 或 '-50%' (减速)
    """
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    # 将音频存入临时文件
    temp_file = os.path.join(TEMP_FOLDER, f"temp_{uuid.uuid4()}.mp3")
    try:
        await communicate.save(temp_file)
        audio = AudioSegment.from_mp3(temp_file)
        return audio
    finally:
        # 确保临时文件被删除
        if os.path.exists(temp_file):
            os.remove(temp_file)


@app.route('/preview', methods=['POST'])
def preview():
    """试听端点 - 生成短文本音频用于预览"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        voice = data.get('voice', 'zh-CN-XiaoxiaoNeural')
        rate = data.get('rate', '1.0')

        if not text:
            return jsonify({'error': '文本不能为空'}), 400

        if len(text) > 50:
            return jsonify({'error': '文本不能超过50个字符'}), 400

        # 将语速转换为 edge-tts 格式
        try:
            rate_float = float(rate)
            rate_percent = int((rate_float - 1.0) * 100)
            rate_str = f'{rate_percent:+d}%'
        except ValueError:
            rate_str = '+0%'

        # 生成音频
        communicate = edge_tts.Communicate(text, voice, rate=rate_str)
        temp_file = os.path.join(TEMP_FOLDER, f"preview_{uuid.uuid4()}.mp3")

        try:
            asyncio.run(communicate.save(temp_file))
            return send_file(temp_file, mimetype='audio/mpeg')
        finally:
            # 延迟删除临时文件，确保音频传输完成
            import threading
            def delayed_remove():
                import time
                time.sleep(5)
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            threading.Thread(target=delayed_remove).start()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/convert', methods=['POST'])
def convert():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400

        # 检查文件大小限制（50MB）
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置文件指针
        
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'文件大小超过限制（最大{MAX_FILE_SIZE//1024//1024}MB）'}), 400

        voice = request.form.get('voice', 'zh-CN-XiaoxiaoNeural')
        rate = request.form.get('rate', '1.0')

        # 将语速转换为 edge-tts 格式
        # 1.0 -> '+0%', 1.5 -> '+50%', 0.8 -> '-20%'
        try:
            rate_float = float(rate)
            rate_percent = int((rate_float - 1.0) * 100)
            rate_str = f'{rate_percent:+d}%'
        except ValueError:
            rate_str = '+0%'

        task_id = str(uuid.uuid4())
        srt_path = os.path.join(UPLOAD_FOLDER, f"{task_id}.srt")
        output_path = os.path.join(UPLOAD_FOLDER, f"{task_id}.mp3")

        file.save(srt_path)

        # 检查字幕文件行数限制
        with open(srt_path, 'r', encoding='utf-8') as f:
            line_count = sum(1 for _ in f)
        
        MAX_LINES = 10000  # 限制字幕行数
        if line_count > MAX_LINES:
            os.remove(srt_path)
            return jsonify({'error': f'字幕文件过大（最多{MAX_LINES}行）'}), 400

        subs = pysrt.open(srt_path)
        total_segments = len(subs)

        # 限制字幕段数
        MAX_SEGMENTS = 1000
        if total_segments > MAX_SEGMENTS:
            os.remove(srt_path)
            return jsonify({'error': f'字幕段数过多（最多{MAX_SEGMENTS}段）'}), 400

        # 初始化进度
        conversion_progress[task_id] = {
            'status': 'processing',
            'current': 0,
            'total': total_segments,
            'output_path': output_path
        }

        # 初始化一个空白音频
        final_audio = AudioSegment.empty()
        last_end_time = 0

        # 循环处理每一段
        for i, sub in enumerate(subs):
            # 计算当前字幕开始时间（毫秒）
            start_ms = sub.start.ordinal
            # 插入静音，确保时间轴对齐
            silence_duration = start_ms - last_end_time
            if silence_duration > 0:
                final_audio += AudioSegment.silent(duration=silence_duration)

            # 生成当前段语音
            segment_audio = asyncio.run(generate_segment(sub.text, voice, rate_str))
            final_audio += segment_audio

            last_end_time = sub.end.ordinal

            # 更新进度
            conversion_progress[task_id]['current'] = i + 1

        final_audio.export(output_path, format="mp3")

        # 清理上传的 SRT 文件
        if os.path.exists(srt_path):
            os.remove(srt_path)

        # 标记为完成
        conversion_progress[task_id]['status'] = 'completed'

        return jsonify({'task_id': task_id})

    except Exception as e:
        # 标记为失败
        if 'task_id' in locals():
            conversion_progress[task_id]['status'] = 'failed'
            conversion_progress[task_id]['error'] = str(e)
        
        # 清理临时文件
        if 'srt_path' in locals() and os.path.exists(srt_path):
            os.remove(srt_path)
            
        return jsonify({'error': str(e)}), 500


@app.route('/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """获取转换进度"""
    if task_id not in conversion_progress:
        return jsonify({'error': '任务不存在'}), 404

    progress = conversion_progress[task_id]
    return jsonify({
        'status': progress['status'],
        'current': progress['current'],
        'total': progress['total'],
        'percentage': int((progress['current'] / progress['total']) * 100) if progress['total'] > 0 else 0,
        'error': progress.get('error', None)
    })


@app.route('/download/<task_id>', methods=['GET'])
def download(task_id):
    """下载转换后的文件"""
    if task_id not in conversion_progress:
        return jsonify({'error': '任务不存在'}), 404

    progress = conversion_progress[task_id]
    if progress['status'] != 'completed':
        return jsonify({'error': '任务未完成'}), 400

    output_path = progress['output_path']
    if not os.path.exists(output_path):
        return jsonify({'error': '文件不存在'}), 404

    return send_file(output_path, as_attachment=True, download_name='output.mp3')


@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    # 启动时清理临时文件
    cleanup_temp_files()
    # 必须指定 host='0.0.0.0'，否则容器外无法访问
    app.run(host='0.0.0.0', port=5000, debug=False)
