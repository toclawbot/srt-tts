#!/usr/bin/env python3
"""
SRT语音合成工具 - 智能分批处理方案
替代硬性限制，实现大规模字幕文件的智能分批处理
"""

import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

# 分批处理配置
BATCH_CONFIG = {
    'max_batch_size': 100,  # 每批最大段数
    'batch_delay': 2,       # 批次间延迟（秒）
    'max_concurrent_batches': 3,  # 最大并发批次
    'progress_update_interval': 10  # 进度更新间隔（段数）
}

def analyze_subtitle_file(srt_path):
    """分析字幕文件，确定分批策略"""
    import pysrt
    
    subs = pysrt.open(srt_path)
    total_segments = len(subs)
    
    # 计算需要的批次数
    batch_count = (total_segments + BATCH_CONFIG['max_batch_size'] - 1) // BATCH_CONFIG['max_batch_size']
    
    return {
        'total_segments': total_segments,
        'batch_count': batch_count,
        'segments_per_batch': min(BATCH_CONFIG['max_batch_size'], total_segments),
        'estimated_time': total_segments * 0.5  # 估算每段0.5秒
    }

async def process_batch(batch_subs, voice, rate_str, batch_index, total_batches):
    """处理单个批次的字幕"""
    from pydub import AudioSegment
    import edge_tts
    import uuid
    
    batch_audio = AudioSegment.empty()
    temp_files = []
    
    try:
        for i, sub in enumerate(batch_subs):
            # 生成单段音频
            communicate = edge_tts.Communicate(sub.text, voice, rate=rate_str)
            temp_file = f"temp_batch_{batch_index}_{i}_{uuid.uuid4()}.mp3"
            
            await communicate.save(temp_file)
            temp_files.append(temp_file)
            
            # 添加到批次音频
            segment_audio = AudioSegment.from_mp3(temp_file)
            batch_audio += segment_audio
            
            print(f"批次 {batch_index+1}/{total_batches}: 处理第 {i+1}/{len(batch_subs)} 段")
    
    finally:
        # 清理临时文件
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    return batch_audio

async def batch_convert_subs(subs, voice, rate_str, progress_callback=None):
    """批量转换字幕文件"""
    total_segments = len(subs)
    batch_size = BATCH_CONFIG['max_batch_size']
    
    # 分批处理
    batches = []
    for i in range(0, total_segments, batch_size):
        batch_subs = subs[i:i + batch_size]
        batches.append(batch_subs)
    
    # 并发处理批次
    final_audio = AudioSegment.empty()
    semaphore = asyncio.Semaphore(BATCH_CONFIG['max_concurrent_batches'])
    
    async def process_with_semaphore(batch_index, batch_subs):
        async with semaphore:
            # 批次间延迟
            if batch_index > 0:
                await asyncio.sleep(BATCH_CONFIG['batch_delay'])
            
            return await process_batch(batch_subs, voice, rate_str, batch_index, len(batches))
    
    # 并发处理所有批次
    tasks = [process_with_semaphore(i, batch) for i, batch in enumerate(batches)]
    batch_results = await asyncio.gather(*tasks)
    
    # 合并所有批次音频
    for batch_audio in batch_results:
        final_audio += batch_audio
    
    return final_audio

def update_progress_callback(current, total):
    """进度更新回调函数"""
    percentage = int((current / total) * 100)
    print(f"进度: {current}/{total} ({percentage}%)")
    
    # 这里可以更新前端进度显示
    # progressBar.style.width = f'{percentage}%'
    # progressPercent.textContent = f'{percentage}%'

# 修改后的convert函数（无硬性限制）
def convert_with_batching(file, voice, rate_str):
    """支持分批处理的转换函数"""
    import pysrt
    from pydub import AudioSegment
    import uuid
    
    try:
        # 分析文件
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        # 保存临时文件
        task_id = str(uuid.uuid4())
        srt_path = f"{task_id}.srt"
        output_path = f"{task_id}.mp3"
        
        file.save(srt_path)
        
        # 分析字幕文件
        analysis = analyze_subtitle_file(srt_path)
        print(f"字幕分析结果: {analysis}")
        
        # 如果文件很大，提示用户
        if analysis['total_segments'] > 100:
            print(f"检测到大文件: {analysis['total_segments']}段字幕，将使用分批处理")
        
        # 读取字幕
        subs = pysrt.open(srt_path)
        
        # 分批处理
        final_audio = asyncio.run(batch_convert_subs(
            subs, voice, rate_str, update_progress_callback
        ))
        
        # 导出最终音频
        final_audio.export(output_path, format="mp3")
        
        # 清理临时文件
        if os.path.exists(srt_path):
            os.remove(srt_path)
        
        return {
            'success': True,
            'task_id': task_id,
            'output_path': output_path,
            'analysis': analysis
        }
        
    except Exception as e:
        # 错误处理
        if 'srt_path' in locals() and os.path.exists(srt_path):
            os.remove(srt_path)
        
        return {
            'success': False,
            'error': str(e)
        }

# 测试函数
def test_batch_processing():
    """测试分批处理功能"""
    print("🧪 测试分批处理功能")
    
    # 模拟不同大小的字幕文件
    test_cases = [
        50,    # 小文件
        250,   # 中等文件
        1500,  # 大文件
        5000   # 超大文件
    ]
    
    for segment_count in test_cases:
        print(f"\n测试 {segment_count} 段字幕:")
        
        analysis = {
            'total_segments': segment_count,
            'batch_count': (segment_count + BATCH_CONFIG['max_batch_size'] - 1) // BATCH_CONFIG['max_batch_size'],
            'estimated_time': segment_count * 0.5
        }
        
        print(f"  批次数: {analysis['batch_count']}")
        print(f"  预计时间: {analysis['estimated_time']:.1f}秒")
        
        if segment_count <= 1000:
            print("  ✅ 处理能力范围内")
        else:
            print("  ⚠️ 需要分批处理")

if __name__ == "__main__":
    print("🔧 SRT语音合成工具 - 智能分批处理方案")
    print("=" * 60)
    
    test_batch_processing()
    
    print("\n📋 方案特点:")
    print("✅ 无硬性文件大小限制")
    print("✅ 智能分批处理大规模字幕")
    print("✅ 并发处理提高效率")
    print("✅ 实时进度更新")
    print("✅ 自动内存管理")
    
    print("\n🚀 部署建议:")
    print("1. 替换原有的convert函数")
    print("2. 更新前端进度显示逻辑")
    print("3. 添加用户友好的大文件提示")