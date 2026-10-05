FROM python:3.13-slim
# 装 gcc 让 asyncmy（无 3.13 wheel）源码编译；用 --no-install-recommends 减小镜像
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev libffi-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]