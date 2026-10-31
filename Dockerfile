FROM python:3.12-slim

WORKDIR /app

# 运行时依赖（不含 playwright，登录在宿主机完成）
COPY requirements-docker.txt .
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
RUN pip install --no-cache-dir -r requirements-docker.txt

# 复制源代码
COPY server/ ./server/

# 数据目录挂载点
RUN mkdir -p /app/db

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
