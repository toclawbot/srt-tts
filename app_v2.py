#!/usr/bin/env python3
"""
SRT到TTS转换器 - v2版本（分段生成 + 音频拼接）
分段生成每段字幕音频，然后拼接成完整音频
"""

import os
import uuid
import shutil
import subprocess
from flask import Flask, render_template, request, send_file, jsonify
import edge_tts
import pysrt
import asyncio
import threading
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
    """主页"""
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    """转换SRT文件为音频"""
    try:
        # 检查文件
        if 'file' not in request.files:
            return jsonify({'error': '没有文件上传'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 获取参数
        voice = request.form.get('voice', 'zh-CN-XiaoxiaoNeural')
        rate = request.form.get('rate', '1.0')
        
        # 转换rate格式
        try:
            rate_float = float(rate)
            rate_percent = int((rate_float - 1.0) * 100)
            rate_str = f'{rate_percent:+d}%'
        except ValueError:
            rate_str = '+0%'
        
        # 保存上传的文件
        srt_filename = f"{uuid.uuid4()}.srt"
        srt_path = os.path.join(UPLOAD_FOLDER, srt_filename)
        file.save(srt_path)
        
        # 解析SRT文件
        try:
            subs = pysrt.open(srt_path)
            total_segments = len(subs)
        except Exception as e:
            return jsonify({'error': f'SRT文件解析失败: {e}'}), 400
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        output_path = os.path.join(TEMP_FOLDER, f"output_{task_id}.wav")
        
        # 初始化进度
        conversion_progress[task_id] = {
            'status': 'processing',
            'current': 0,
            'total': total_segments,
            'output_path': output_path,
            'percentage': 0
        }

        # 立即返回任务ID，避免前端超时
        # 在后台处理音频转换
        def process_audio_in_background():
            try:
                if total_segments > 0:
                    audio_segments = []
                    
                    for i, sub in enumerate(subs):
                        # 更新进度
                        conversion_progress[task_id]['current'] = i + 1
                        conversion_progress[task_id]['percentage'] = int(((i + 1) / total_segments) * 100)
                        
                        print(f"处理进度: {i+1}/{total_segments} ({conversion_progress[task_id]['percentage']}%)")
                        
                        # 生成单段音频
                        communicate = edge_tts.Communicate(sub.text, voice, rate=rate_str)
                        segment_path = os.path.join(TEMP_FOLDER, f"segment_{uuid.uuid4()}.wav")
                        
                        # 使用异步运行
                        try:
                            asyncio.run(communicate.save(segment_path))
                        except RuntimeError as e:
                            # 如果事件循环已经在运行，使用 nest_asyncio
                            import nest_asyncio
                            nest_asyncio.apply()
                            asyncio.run(communicate.save(segment_path))
                        
                        # 检查文件是否成功生成
                        if not os.path.exists(segment_path) or os.path.getsize(segment_path) == 0:
                            raise Exception(f"音频文件生成失败: {segment_path}")
                        
                        # 加载音频段 - 使用 from_file 自动检测格式
                        try:
                            segment = AudioSegment.from_file(segment_path)
                        except Exception as e:
                            print(f"加载音频失败，尝试使用 ffmpeg 重新编码: {e}")
                            # 如果直接加载失败，尝试使用 ffmpeg 重新编码
                            temp_path = segment_path.replace('.wav', '_fixed.wav')
                            try:
                                subprocess.run(
                                    ['ffmpeg', '-y', '-i', segment_path, temp_path],
                                    check=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE
                                )
                                if os.path.exists(temp_path):
                                    segment = AudioSegment.from_file(temp_path)
                                    os.remove(temp_path)
                                else:
                                    raise Exception("ffmpeg 重新编码失败")
                            except subprocess.CalledProcessError as ffmpeg_error:
                                print(f"ffmpeg 错误: {ffmpeg_error.stderr.decode()}")
                                raise
                        
                        # 计算需要的静音时长
                        if i == 0:
                            # 第一个字幕段：检查是否需要添加起始静音
                            start_ms = sub.start.ordinal
                            if start_ms > 0:
                                silence = AudioSegment.silent(duration=start_ms)
                                audio_segments.append(silence)
                        else:
                            # 后续字幕段：计算与前一段的时间间隔
                            time_gap = sub.start - subs[i-1].end
                            gap_ms = time_gap.ordinal  # 毫秒
                            
                            # 如果当前音频段比时间间隔短，添加静音
                            if gap_ms > 0:
                                silence = AudioSegment.silent(duration=gap_ms)
                                audio_segments.append(silence)
                        
                        audio_segments.append(segment)
                        
                        # 清理临时段文件
                        os.remove(segment_path)
                    
                    # 拼接所有音频段
                    if audio_segments:
                        final_audio = audio_segments[0]
                        for segment in audio_segments[1:]:
                            final_audio += segment
                        
                        # 导出最终音频
                        final_audio.export(output_path, format="wav")
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
        
        return jsonify({'error': str(e)}), 500

@app.route('/progress/<task_id>', methods=['GET'])
def progress(task_id):
    """获取转换进度"""
    if task_id not in conversion_progress:
        return jsonify({'error': '任务不存在'}), 404
        
    progress = conversion_progress[task_id]
    return jsonify(progress)


@app.route('/download/<task_id>', methods=['GET'])
@app.route('/download/<task_id>.wav', methods=['GET'])
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


@app.route('/preview', methods=['POST'])
def preview():
    """试听功能 - 生成并返回试听音频"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
            
        text = data.get('text', '').strip()
        voice = data.get('voice', 'zh-CN-XiaoxiaoNeural')
        rate = data.get('rate', '1.0')
        
        if not text:
            return jsonify({'error': '试听文本不能为空'}), 400
            
        # 限制文本长度
        if len(text) > 50:
            return jsonify({'error': '试听文本不能超过50个字符'}), 400
        
        # 转换rate格式
        try:
            rate_float = float(rate)
            rate_percent = int((rate_float - 1.0) * 100)
            rate_str = f'{rate_percent:+d}%'
        except ValueError:
            rate_str = '+0%'
        
        # 生成临时文件路径
        task_id = str(uuid.uuid4())
        output_path = os.path.join(TEMP_FOLDER, f'preview_{task_id}.wav')
        
        # 使用edge-tts生成音频
        communicate = edge_tts.Communicate(text, voice, rate=rate_str)
        
        # 使用异步运行
        try:
            asyncio.run(communicate.save(output_path))
        except RuntimeError as e:
            # 如果事件循环已经在运行，使用 nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()
            asyncio.run(communicate.save(output_path))
        
        # 检查文件是否成功生成
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            return jsonify({'error': '音频文件生成失败'}), 500
        
        # 返回音频文件
        return send_file(output_path, mimetype='audio/wav')
        
    except Exception as e:
        print(f"试听生成错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    # 启动时清理临时文件
    cleanup_temp_files()
    # 必须指定 host='0.0.0.0'，否则容器外无法访问
    app.run(host='0.0.0.0', port=5000, debug=False)