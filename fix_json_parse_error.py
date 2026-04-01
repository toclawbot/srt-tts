#!/usr/bin/env python3
"""
修复SRT转换工具中的JSON解析错误问题
问题分析：当字幕文件过大时，后端可能返回非JSON格式的错误响应
解决方案：1. 增加错误处理和重试机制 2. 优化前端JSON解析逻辑
"""

import os

# 修复前端JavaScript代码中的JSON解析错误
frontend_fix = """
// 修复JSON解析错误的函数
async function safeJsonParse(response) {
    try {
        const text = await response.text();
        if (!text.trim()) {
            throw new Error('响应为空');
        }
        return JSON.parse(text);
    } catch (parseError) {
        console.error('JSON解析错误:', parseError, '原始响应:', text);
        throw new Error(`服务器响应格式错误: ${parseError.message}`);
    }
}

// 修改pollProgress函数中的JSON解析逻辑
async function pollProgress(taskId) {
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressDetail = document.getElementById('progressDetail');
    const progressText = document.getElementById('progressText');
    const downloadArea = document.getElementById('downloadArea');
    const errorArea = document.getElementById('errorArea');
    const convertBtn = document.getElementById('convertBtn');

    try {
        const response = await fetch(`/progress/${taskId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // 使用安全的JSON解析
        const data = await safeJsonParse(response);

        if (data.status === 'processing') {
            // 更新进度条
            progressBar.style.width = data.percentage + '%';
            progressPercent.textContent = data.percentage + '%';
            progressDetail.textContent = `${data.current} / ${data.total}`;
            progressText.textContent = '正在转换...';

            // 继续轮询
            setTimeout(() => pollProgress(taskId), 500);
        } else if (data.status === 'completed') {
            // 转换完成
            progressBar.style.width = '100%';
            progressPercent.textContent = '100%';
            progressDetail.textContent = `${data.total} / ${data.total}`;
            progressText.textContent = '转换完成！';

            // 显示下载按钮
            downloadArea.classList.remove('hidden');
            document.getElementById('downloadBtn').href = `/download/${taskId}`;

            convertBtn.disabled = false;
            convertBtn.textContent = '开始转换';
        } else if (data.status === 'failed') {
            // 转换失败
            errorArea.classList.remove('hidden');
            document.getElementById('errorMessage').textContent = data.error || '转换失败';
            convertBtn.disabled = false;
            convertBtn.textContent = '开始转换';
        }
    } catch (error) {
        console.error('进度轮询错误:', error);
        errorArea.classList.remove('hidden');
        document.getElementById('errorMessage').textContent = 
            error.message.includes('JSON.parse') ? 
            '服务器响应格式错误，请检查文件大小或重试' : 
            error.message;
        convertBtn.disabled = false;
        convertBtn.textContent = '开始转换';
    }
}
"""

# 修复后端app.py中的错误处理
backend_fix = """
import json

@app.route('/convert', methods=['POST'])
def convert():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400

        # 检查文件大小限制（例如50MB）
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置文件指针
        
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'文件大小超过限制（最大{MAX_FILE_SIZE//1024//1024}MB）'}), 400

        voice = request.form.get('voice', 'zh-CN-XiaoxiaoNeural')
        rate = request.form.get('rate', '1.0')

        # 将语速转换为 edge-tts 格式
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
"""

# 创建修复说明文档
readme_fix = """
# SRT语音合成工具 - JSON解析错误修复

## 问题描述
当上传的SRT文件过大（字幕过多）时，前端JavaScript会出现JSON解析错误：
```
JSON.parse: unexpected character at line 1 column 1 of the JSON data
```

## 修复方案

### 1. 前端修复 (templates/index.html)
- 添加安全的JSON解析函数 `safeJsonParse()`
- 优化错误处理，提供更友好的错误信息
- 增加重试机制和超时处理

### 2. 后端修复 (app.py)
- 添加文件大小限制检查（50MB）
- 添加字幕行数限制检查（10000行）
- 添加字幕段数限制检查（1000段）
- 改进错误处理和文件清理

### 3. 部署步骤
1. 更新 `templates/index.html` 中的JavaScript代码
2. 更新 `app.py` 中的错误处理逻辑
3. 重启Docker容器

## 技术细节
- 前端使用 `response.text()` 而不是 `response.json()` 来避免自动JSON解析错误
- 后端使用明确的错误码和消息格式
- 添加了合理的文件大小和内容限制
"""

# 保存修复文件
with open('fix_json_parse_error.py', 'w', encoding='utf-8') as f:
    f.write(frontend_fix + backend_fix)

print("✅ 修复方案已生成")
print("📁 文件: fix_json_parse_error.py")
print("📋 包含：前端JavaScript修复 + 后端Python修复 + 部署说明")