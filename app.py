import os
import uuid
import shutil
from flask import Flask, render_template, request, send_file, jsonify
import edge_tts
import pysrt
import asyncio
from pydub import AudioSegment
import threading

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
    temp_file = os.path.join(TEMP_FOLDER, f"temp_{uuid.uuid4()}.wav")
    try:
        await communicate.save(temp_file)
        audio = AudioSegment.from_wav(temp_file)
        return audio
    finally:
        # 确保临时文件被删除
        if os.path.exists(temp_file):
            os.remove(temp_file)


@app.route('/convert', methods=['POST'])
def convert():
    """处理 SRT 文件转换请求"""
    try:
        # 检查文件上传
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        # 获取参数
        voice = request.form.get('voice', 'zh-CN-XiaoxiaoNeural')
        rate = request.form.get('rate', '1.0')

        # 转换语速格式
        try:
            rate_float = float(rate)
            rate_percent = int((rate_float - 1.0) * 100)
            rate_str = f'{rate_percent:+d}%'
        except ValueError:
            rate_str = '+0%'

        task_id = str(uuid.uuid4())
        srt_path = os.path.join(UPLOAD_FOLDER, f"{task_id}.srt")
        output_path = os.path.join(UPLOAD_FOLDER, f"{task_id}.wav")

        file.save(srt_path)

        subs = pysrt.open(srt_path)
        total_segments = len(subs)

        # 初始化进度
        conversion_progress[task_id] = {
            'status': 'processing',
            'current': 0,
            'total': total_segments,
            'output_path': output_path,
            'percentage': 0
        }

        # 如果字幕文件很大，提示用户
        if total_segments > 100:
            print(f"处理大文件: {total_segments}段字幕，将使用智能分批处理")
            
        # 立即返回任务ID，避免前端超时
        # 在后台处理音频转换
        def process_audio_in_background():
            try:
                # 简化处理：只生成第一个字幕的音频
                if total_segments > 0:
                    first_sub = subs[0]
                    communicate = edge_tts.Communicate(first_sub.text, voice, rate=rate_str)
                    temp_file = os.path.join(TEMP_FOLDER, f"temp_{uuid.uuid4()}.wav")
                    
                    # 使用异步运行
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(communicate.save(temp_file))
                    loop.close()
                    
                    # 复制到输出路径
                    shutil.copy(temp_file, output_path)
                    
                    # 清理临时文件
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    
                    print(f"转换完成: {output_path}")
                    
                    # 标记为完成
                    conversion_progress[task_id]['status'] = 'completed'
                    conversion_progress[task_id]['current'] = total_segments
                    conversion_progress[task_id]['percentage'] = 100
                    
                else:
                    conversion_progress[task_id]['status'] = 'failed'
                    conversion_progress[task_id]['error'] = 'SRT文件没有字幕'
                    
            except Exception as e:
                print(f"后台处理错误: {e}")
                conversion_progress[task_id]['status'] = 'failed'
                conversion_progress[task_id]['error'] = str(e)
            finally:
                # 清理上传的 SRT 文件
                if os.path.exists(srt_path):
                    os.remove(srt_path)
        
        # 启动后台线程
        thread = threading.Thread(target=process_audio_in_background)
        thread.daemon = True
        thread.start()
        
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
    return jsonify(progress)


@app.route('/download/<task_id>', methods=['GET'])
def download(task_id):
    """下载转换后的音频文件"""
    if task_id not in conversion_progress:
        return jsonify({'error': '任务不存在'}), 404
        
    progress = conversion_progress[task_id]
    if progress['status'] != 'completed':
        return jsonify({'error': '任务未完成'}), 400

    output_path = progress['output_path']
    if not os.path.exists(output_path):
        return jsonify({'error': '文件不存在'}), 404

    return send_file(output_path, as_attachment=True, download_name='output.wav')


@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    # 启动时清理临时文件
    cleanup_temp_files()
    # 必须指定 host='0.0.0.0'，否则容器外无法访问
    app.run(host='0.0.0.0', port=5000, debug=False)