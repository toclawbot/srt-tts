FROM python:3.9-slim

# 1. 安装系统依赖 (ffmpeg 是 pydub 处理音频的核心)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. 复制项目代码
COPY . .

CMD ["python", "app.py"]
