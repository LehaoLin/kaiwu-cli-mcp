# Kaiwu SDK Docker 镜像
# 玻色量子 CIM 相干光量子计算机 Python SDK 环境
# 文档: https://kaiwu-sdk-docs.qboson.com/zh/latest/index.html

FROM python:3.10-slim

LABEL maintainer="kaiwu-cli-mcp"
LABEL description="Kaiwu SDK Docker environment for 玻色量子 CIM quantum computer"

# 安装系统依赖（unzip 用于解压 SDK 安装包）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /workspace

# 复制 Kaiwu SDK 安装包（支持 .whl 或 .zip）
# 从 https://platform.qboson.com/sdkDownload 下载 Linux 版本
# 将下载的文件放入项目 ./sdk/ 目录
COPY sdk/ /tmp/sdk/

# 安装 Kaiwu SDK（自动处理 .zip 解压 → pip install .whl）
RUN if ls /tmp/sdk/*.zip 1>/dev/null 2>&1; then \
        unzip -q /tmp/sdk/*.zip -d /tmp/sdk/ && rm /tmp/sdk/*.zip; \
    fi \
    && pip install --no-cache-dir /tmp/sdk/*.whl -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && rm -rf /tmp/sdk

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
