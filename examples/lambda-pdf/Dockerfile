# AWS's Python image includes the runtime client and local runtime emulator.
ARG LAMBDA_BASE=public.ecr.aws/lambda/python:3.13-x86_64@sha256:8391efd70b63a46c3c4980a7db4480ac09e5289cada4d39d454e843c51bae82d
FROM ${LAMBDA_BASE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN python -m pip install --no-cache-dir --only-binary=:all: --no-deps -r requirements.txt --target "${LAMBDA_TASK_ROOT}" --report "${LAMBDA_TASK_ROOT}/pip-install.json"
COPY handler.py ${LAMBDA_TASK_ROOT}/
COPY templates/ ${LAMBDA_TASK_ROOT}/templates/
COPY fonts/ ${LAMBDA_TASK_ROOT}/fonts/
# Lambda supplies a least-privileged user. Local checks also use a numeric user.
CMD ["handler.handler"]
