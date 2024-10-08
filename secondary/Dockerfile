FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# # Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY .dockerignore /app/.dockerignore

ADD . /app

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []

USER root

CMD ["bash", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port 8000"]
