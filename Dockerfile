# --- 第一阶段：构建环境 ---
FROM python:3.9-slim AS builder
WORKDIR /app
# 安装编译环境
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev
COPY requirements.txt .
# 安装依赖到指定目录
RUN pip install --user --no-cache-dir -r requirements.txt

# --- 第二阶段：运行环境 ---
FROM python:3.9-slim
# 只安装 ffmpeg 运行时库
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
# 从构建阶段拷贝安装好的库
COPY --from=builder /root/.local /root/.local
COPY . .

# 设置环境变量，确保能找到 pip 安装的库
ENV PATH=/root/.local/bin:$PATH

CMD ["python", "app.py"]
