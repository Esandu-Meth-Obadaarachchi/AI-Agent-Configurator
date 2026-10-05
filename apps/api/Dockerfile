# The configurator engine + API. Build from the repo root:
#   docker build -f apps/api/Dockerfile -t agent-configurator-api .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps/api ./apps/api
COPY modules ./modules
COPY examples/specs ./examples/specs
RUN pip install ".[api]"
# The engine finds templates and blueprints next to the installed package.
ENV CONFIGURATOR_MODULES_DIR=/srv/modules
EXPOSE 8787
CMD ["uvicorn", "configurator_api.main:app", "--host", "0.0.0.0", "--port", "8787"]
