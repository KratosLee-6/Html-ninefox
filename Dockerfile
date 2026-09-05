# ============================================================
# Html九尾狐 v0.4.1 · All-in-one 镜像（源码 → wheel → 运行时）
# 构建:  docker build -t htmlninefox .
# 运行:  docker run -p 8620:8620 -e MINIMAX_API_KEY=xxx htmlninefox
# ============================================================

# ---------- 构建阶段：从源码打 wheel ----------
FROM python:3.13-slim AS builder
WORKDIR /src
COPY pyproject.toml uv.lock README.md ./
COPY htmlninefox ./htmlninefox
RUN python -m pip install --no-cache-dir build \
    && python -m build --wheel --outdir /dist

# ---------- 运行阶段 ----------
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/fox

RUN useradd --create-home --uid 10001 fox
WORKDIR /app
COPY --from=builder /dist/*.whl /tmp/htmlninefox.whl
RUN python -m pip install --no-cache-dir /tmp/htmlninefox.whl && rm /tmp/htmlninefox.whl

USER fox
VOLUME ["/home/fox/.htmlninefox", "/home/fox/htmlninefox-output"]
EXPOSE 8620

# Web 工作台入口（真实 LLM 通过 MINIMAX_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY 注入）
CMD ["htmlninefox", "workbench", "--host", "0.0.0.0", "--port", "8620", \
     "--output", "/home/fox/htmlninefox-output", "--no-open-browser"]
