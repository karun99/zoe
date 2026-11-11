FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml requirements.txt README.md ./
COPY zoe ./zoe

RUN pip install --upgrade pip \
    && pip install .

# The companion talks to Ollama or llama-server over plain HTTP, so no model
# weights are baked into the image. Point ZOE_OLLAMA_URL at a reachable host.
ENV ZOE_OLLAMA_URL=http://host.docker.internal:11434

ENTRYPOINT ["zoe"]
CMD ["--help"]
