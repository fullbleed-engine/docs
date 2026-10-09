# SPDX-License-Identifier: MIT
FROM python:3.14.8-slim-bookworm@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --only-binary=:all: --no-cache-dir --report /app/pip-install.json -r requirements.txt && python -m pip check
COPY renderer/ ./
COPY server.py ./
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--no-access-log", "--limit-concurrency", "8", "--timeout-keep-alive", "5"]
