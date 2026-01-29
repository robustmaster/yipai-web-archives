FROM python:3.9-slim

WORKDIR /app

# 安装必要的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖配置
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制整个项目目录（包括 templates 和 static）
COPY . .

# 暴露端口
EXPOSE 5000

# 使用 Gunicorn 启动
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "--workers", "2", "--timeout", "120"]