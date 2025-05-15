#
# Base image with defaults for all stages
FROM registry.access.redhat.com/ubi9-minimal@sha256:21ed5a01130d3a77eb4a26a80de70a4433860255b394e95dc2c26817de1da061 AS base

COPY LICENSE /licenses/

ENV APP_ROOT=/opt/app-root
ENV \
    # use venv from ubi image
    UV_PROJECT_ENVIRONMENT=${APP_ROOT} \
    # compile bytecode for faster startup
    UV_COMPILE_BYTECODE="true" \
    # disable uv cache. it doesn't make sense in a container
    UV_NO_CACHE=true \
    BASH_ENV="${APP_ROOT}/bin/activate" \
    ENV="${APP_ROOT}/bin/activate" \
    PROMPT_COMMAND=". ${APP_ROOT}/bin/activate"

# Install base dependencies
RUN microdnf install -y python3.12 make && microdnf clean all
USER 1001
WORKDIR ${APP_ROOT}/src


#
# Builder image
#
FROM registry.access.redhat.com/ubi9/python-312@sha256:aa2a3c086013ce259af562ddc64c5aa55471c42a2a8a731f185767e86a94283b AS builder
COPY --from=ghcr.io/astral-sh/uv:0.7.4@sha256:9618e472e7ed9aa980719c68e51416e7ec23d85742d9ccca5c817d76ed2eb5aa /uv /bin/uv
ENV \
    # use venv from ubi image
    UV_PROJECT_ENVIRONMENT=${APP_ROOT} \
    # compile bytecode for faster startup
    UV_COMPILE_BYTECODE="true" \
    # disable uv cache. it doesn't make sense in a container
    UV_NO_CACHE=true

COPY packages/automated_actions/pyproject.toml uv.lock ./
# Install the project dependencies
RUN uv sync --frozen --no-install-project --no-group dev

COPY README.md ./
COPY --chown=1001:root packages/automated_actions packages/automated_actions
RUN uv sync --frozen --no-group dev


#
# Test image
#
FROM base AS test
COPY --from=ghcr.io/astral-sh/uv:0.7.4@sha256:9618e472e7ed9aa980719c68e51416e7ec23d85742d9ccca5c817d76ed2eb5aa /uv /bin/uv

COPY Makefile ./
COPY --from=builder /opt/app-root /opt/app-root
RUN uv sync --frozen --verbose
RUN make test


#
# Production image
#
FROM base AS prod
COPY --from=builder /opt/app-root /opt/app-root
COPY app.sh ./
ENTRYPOINT [ "./app.sh" ]
