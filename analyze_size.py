#!/usr/bin/env python3
"""
分析Docker镜像大小优化效果
"""

# 基础镜像大小对比
BASE_IMAGES = {
    "python:3.9-alpine": "~45MB",
    "python:3.9-slim": "~55MB"
}

# 依赖包大小估算
PACKAGES = {
    "ffmpeg": "~50MB",
    "sox": "~10MB",
    "Python依赖": "~100MB",
    "编译工具": "~200MB",
    "音频库(lame/libogg等)": "~50MB"
}

print("Docker镜像大小分析")
print("=" * 50)

print("\n原始配置（Alpine + 完整依赖）:")
print(f"- 基础镜像: {BASE_IMAGES['python:3.9-alpine']}")
print(f"- ffmpeg: {PACKAGES['ffmpeg']}")
print(f"- sox: {PACKAGES['sox']}")
print(f"- Python依赖: {PACKAGES['Python依赖']}")
print(f"- 编译工具: {PACKAGES['编译工具']}")
print(f"- 音频库: {PACKAGES['音频库(lame/libogg等)']}")
print(f"总估算: ~460MB (压缩后约200MB)")

print("\n优化后配置（Slim + 精简依赖）:")
print(f"- 基础镜像: {BASE_IMAGES['python:3.9-slim']}")
print(f"- ffmpeg: {PACKAGES['ffmpeg']}")
print(f"- sox: {PACKAGES['sox']}")
print(f"- Python依赖: {PACKAGES['Python依赖']}")
print(f"- 移除编译工具: -{PACKAGES['编译工具']}")
print(f"- 移除音频库: -{PACKAGES['音频库(lame/libogg等)']}")
print(f"总估算: ~215MB (压缩后约100MB)")

print("\n优化效果:")
print("✓ 移除不必要的音频库: -50MB")
print("✓ 移除编译工具: -200MB") 
print("✓ 基础镜像略大: +10MB")
print("净减少: ~240MB")

print("\n实际大小可能因缓存和构建方式有所不同")