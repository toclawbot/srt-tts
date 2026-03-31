# --- 第一阶段：构建环境 ---
FROM python:3.9-alpine AS builder

WORKDIR /app

# 安装编译依赖和构建工具
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev

COPY requirements.txt .

# 安装 Python 依赖到系统目录
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- 第二阶段：运行环境 ---
FROM python:3.9-alpine

# 安装运行时依赖（ffmpeg 和音频库）
RUN apk add --no-cache \
    ffmpeg \
    libsoxr \
    lame \
    libogg \
    libvorbis \
    flac \
    opusfile && \
    rm -rf /var/cache/apk/*

WORKDIR /app

# 从构建阶段复制 Python 包
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 5000

CMD ["python", "app.py"]
