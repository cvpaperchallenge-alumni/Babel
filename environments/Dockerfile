ARG BASE_IMAGE=python:3.12.3-slim-bullseye
FROM ${BASE_IMAGE}

ARG PROJECT_NAME=babel
ARG USER_NAME=challenger
ARG GROUP_NAME=challengers
ARG UID=1000
ARG GID=1000
ARG APPLICATION_DIRECTORY=/home/${USER_NAME}/${PROJECT_NAME}
ARG RUN_UV_INSTALL_AT_BUILD_TIME="false"

ENV DEBIAN_FRONTEND="noninteractive" \
    LC_ALL="C.UTF-8" \
    LANG="C.UTF-8" \
    PYTHONPATH=${APPLICATION_DIRECTORY}

RUN apt update && \
    apt install --no-install-recommends -y gcc python3-dev libjpeg-dev zlib1g-dev libpng-dev \
    && pip install --no-cache-dir --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

RUN apt update \
    && apt install --no-install-recommends -y git curl make \
    && rm -rf /var/lib/apt/lists/*

# Install uv from the official image — version-pinned, no Python dependency.
COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /uvx /bin/

# Add user. Without this, following process is executed as admin.
RUN groupadd -g ${GID} ${GROUP_NAME} \
    && useradd -ms /bin/sh -u ${UID} -g ${GID} ${USER_NAME}

USER ${USER_NAME}
WORKDIR ${APPLICATION_DIRECTORY}

# If ${RUN_UV_INSTALL_AT_BUILD_TIME} = "true", install Python packages with uv and move .venv under ${HOME}.
# This process is for CI (GitHub Actions). To prevent overwrite by volume of docker compose, .venv is moved under ${HOME}.
COPY --chown=${UID}:${GID} pyproject.toml uv.lock .
RUN test ${RUN_UV_INSTALL_AT_BUILD_TIME} = "true" && uv sync --frozen || echo "skip to run uv sync."
RUN test ${RUN_UV_INSTALL_AT_BUILD_TIME} = "true" && mv ${APPLICATION_DIRECTORY}/.venv ${HOME}/.venv || echo "skip to move .venv."
