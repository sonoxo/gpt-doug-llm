FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev
COPY app ./app
USER 65532:65532
EXPOSE 8787
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
