# Kaiwu SDK Docker 镜像
# 玻色量子 CIM 相干光量子计算机 Python SDK 环境
# 文档: https://kaiwu-sdk-docs.qboson.com/zh/latest/index.html

FROM python:3.10-slim

LABEL maintainer="kaiwu-cli-mcp"
LABEL description="Kaiwu SDK Docker environment for 玻色量子 CIM quantum computer"

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /workspace

# 复制 Kaiwu SDK wheel 文件
# 请从 https://platform.qboson.com/ 下载 Linux 版本的 SDK
# 文件命名如: kaiwu-1.3.1-cp310-cp310-linux_x86_64.whl
COPY sdk/*.whl /tmp/

# 安装 Kaiwu SDK
RUN pip install --no-cache-dir /tmp/*.whl -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && rm -rf /tmp/*.whl

# 安装常用依赖
RUN pip install --no-cache-dir \
    numpy \
    pyyaml \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 创建用户脚本目录
RUN mkdir -p /user_script

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace:/user_script

# 默认命令
CMD ["python3"]
