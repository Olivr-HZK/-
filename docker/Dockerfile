# 使用多阶段构建或保持 slim 镜像，确保层级清晰
FROM python:3.10-slim

WORKDIR /app

# 复用原有的 Supercronic 安装逻辑（用于定时任务管理）
ARG TARGETARCH
ENV SUPERCRONIC_VERSION=v0.2.39

RUN set -ex && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    case ${TARGETARCH} in \
    amd64) \
    export SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64; \
    export SUPERCRONIC_SHA1SUM=c98bbf82c5f648aaac8708c182cc83046fe48423; \
    export SUPERCRONIC=supercronic-linux-amd64; \
    ;; \
    arm64) \
    export SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-arm64; \
    export SUPERCRONIC_SHA1SUM=5ef4ccc3d43f12d0f6c3763758bc37cc4e5af76e; \
    export SUPERCRONIC=supercronic-linux-arm64; \
    ;; \
    *) \
    echo "Unsupported architecture: ${TARGETARCH}"; \
    exit 1; \
    ;; \
    esac && \
    curl -fsSL -o "$SUPERCRONIC" "$SUPERCRONIC_URL" && \
    echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - && \
    chmod +x "$SUPERCRONIC" && \
    mv "$SUPERCRONIC" "/usr/local/bin/supercronic" && \
    apt-get remove -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ---- 依赖安装阶段 ----
# 0. 基础库安装


# 1. 安装原项目依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium && playwright install-deps chromium

# 2. 安装自定义脚本依赖 (如果你的依赖在 requirements.txt 里已包含，可跳过此行)
# 假设你把 pandas, openai 等写在了 my_requirements.txt
# COPY my_requirements.txt .
# RUN pip install --no-cache-dir -r my_requirements.txt

# ---- 代码注入阶段 ----
# 复制所有核心代码
COPY docker/manage.py .
COPY trendradar/ ./trendradar/

# 3. 复制你的自定义脚本
COPY GTscraper.py .
COPY GTSummaryAI.py .
COPY sender/ ./sender/

# 复制控制脚本并设置权限
COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && \
    chmod +x /entrypoint.sh && \
    chmod +x manage.py && \
    mkdir -p /app/config /app/output

# ---- 运行环境配置 ----
ENV PYTHONUNBUFFERED=1 \
    CONFIG_PATH=/app/config/config.yaml \
    FREQUENCY_WORDS_PATH=/app/config/frequency_words.txt

# 这里的 ENTRYPOINT 不动，它会通过 supercronic 调用 manage.py run
ENTRYPOINT ["/entrypoint.sh"]
