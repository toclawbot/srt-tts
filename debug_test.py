#!/usr/bin/env python3
import asyncio
import edge_tts
import pysrt
import os

async def test_edge_tts():
    """测试edge-tts功能"""
    print("测试edge-tts...")
    try:
        communicate = edge_tts.Communicate("测试文本", "zh-CN-XiaoxiaoNeural")
        await communicate.save("test_output.wav")
        print("edge-tts测试成功")
        return True
    except Exception as e:
        print(f"edge-tts错误: {e}")
        return False

def test_srt_parse():
    """测试SRT解析"""
    print("测试SRT解析...")
    try:
        subs = pysrt.open("test.srt")
        print(f"SRT解析成功: {len(subs)}段字幕")
        return True
    except Exception as e:
        print(f"SRT解析错误: {e}")
        return False

async def test_full_conversion():
    """测试完整转换流程"""
    print("测试完整转换流程...")
    
    # 解析SRT
    subs = pysrt.open("test.srt")
    
    # 处理每段字幕
    for i, sub in enumerate(subs):
        print(f"处理第{i+1}段: {sub.text}")
        try:
            communicate = edge_tts.Communicate(sub.text, "zh-CN-XiaoxiaoNeural")
            await communicate.save(f"segment_{i}.wav")
            print(f"  第{i+1}段处理成功")
        except Exception as e:
            print(f"  第{i+1}段处理失败: {e}")
            return False
    
    print("完整转换测试成功")
    return True

if __name__ == "__main__":
    # 创建测试目录
    os.makedirs("test_output", exist_ok=True)
    # 复制测试文件到输出目录
    import shutil
    if os.path.exists("test.srt"):
        shutil.copy("test.srt", "test_output/test.srt")
    os.chdir("test_output")
    
    # 运行测试
    results = []
    
    # 测试SRT解析
    results.append(test_srt_parse())
    
    # 测试edge-tts
    results.append(asyncio.run(test_edge_tts()))
    
    # 测试完整流程
    results.append(asyncio.run(test_full_conversion()))
    
    print(f"\n测试结果: {sum(results)}/{len(results)} 通过")
    
    # 清理测试文件
    for file in os.listdir("."):
        if file.endswith(".wav"):
            os.remove(file)