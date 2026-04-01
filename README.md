# SRT语音合成工具

将SRT字幕文件转换为语音音频文件的Web工具。

## 🎯 特性

### v1版本（智能拼接）
- ✅ 智能文本拼接
- ✅ 基于时间间隔的标点控制
- ✅ 内存占用低
- ✅ 处理速度快

### v2版本（分段生成）
- ✅ 精确时间轴对齐
- ✅ 分段音频生成
- ✅ 音频拼接技术
- ✅ 高质量语音输出

## 🚀 快速开始

### Docker部署
```bash
# 克隆项目
git clone https://github.com/toclawbot/srt-tts.git
cd srt-tts

# 启动v1版本（推荐）
docker-compose up srt-tts -d

# 启动v2版本
docker-compose up srt-tts-v2 -d
```

### 访问服务
- **v1版本**: http://localhost:5000
- **v2版本**: http://localhost:5001

## 📊 版本对比

| 特性 | v1版本 | v2版本 |
|------|--------|--------|
| 时间轴对齐 | ✅ 智能标点 | ✅ 精确静音 |
| 语音自然度 | ✅ 良好 | ✅ 优秀 |
| 内存占用 | ✅ 低 | ⚠️ 较高 |
| 处理速度 | ✅ 快 | ⚠️ 较慢 |

## 🔧 技术栈

- **后端**: Python Flask + edge-tts
- **前端**: HTML + Tailwind CSS
- **容器**: Docker + Docker Compose
- **部署**: GitHub Actions

## 📚 文档

- [部署指南](DEPLOYMENT_GUIDE.md) - v1版本详细说明
- [v2版本部署指南](DEPLOYMENT_GUIDE_V2.md) - v2版本详细说明

## 🔄 版本管理

- **latest**: 最新稳定版（v1）
- **v1**: 智能拼接版本
- **v2**: 分段生成版本

## 🐛 问题反馈

如有问题请提交 [GitHub Issue](https://github.com/toclawbot/srt-tts/issues)

## 📄 许可证

MIT License