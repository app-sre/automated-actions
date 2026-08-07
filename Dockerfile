#
# Base image with defaults for all stages
FROM registry.access.redhat.com/ubi10/python-314-minimal@sha256:d907e1e16ec2aa81ef53e12e751af3ecc96ec0f9d08df0f6c757e6c95fe20198 AS base

COPY LICENSE /licenses/

ENV APP_ROOT=/opt/app-root
ENV \
    # unbuffered output for easier logging
    PYTHONUNBUFFERED=1 \
    # use venv from ubi image
    UV_PROJECT_ENVIRONMENT=${APP_ROOT} \
    # compile bytecode for faster startup
    UV_COMPILE_BYTECODE="true" \
    # disable uv cache. it doesn't make sense in a container
    UV_NO_CACHE=true \
    BASH_ENV="${APP_ROOT}/bin/activate" \
    ENV="${APP_ROOT}/bin/activate" \
    PROMPT_COMMAND=". ${APP_ROOT}/bin/activate" \
    IS_TESTED_FLAG="/tmp/is_tested"

WORKDIR ${APP_ROOT}/src

USER 0
# Install base dependencies
RUN microdnf install -y make && microdnf clean all
USER 1001

#
# Builder image
#
FROM registry.access.redhat.com/ubi10/python-314-minimal@sha256:d907e1e16ec2aa81ef53e12e751af3ecc96ec0f9d08df0f6c757e6c95fe20198 AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.3@sha256:2d890623d310b57771ce840f0da5eed5fc6d657da05ffaa45d82797b53fa3abc /uv /bin/uv
ENV \
    # use venv from ubi image
    UV_PROJECT_ENVIRONMENT=${APP_ROOT} \
    # compile bytecode for faster startup
    UV_COMPILE_BYTECODE="true" \
    # disable uv cache. it doesn't make sense in a container
    UV_NO_CACHE=true

COPY --chown=1001:root packages/automated_actions_utils packages/automated_actions_utils
COPY --chown=1001:root packages/automated_actions packages/automated_actions
COPY --chown=1001:root README.md pyproject.toml uv.lock ./
RUN cd packages/automated_actions && uv sync --frozen --no-group dev --verbose

#
# Test image
#
FROM base AS test
COPY --from=ghcr.io/astral-sh/uv:0.12.3@sha256:2d890623d310b57771ce840f0da5eed5fc6d657da05ffaa45d82797b53fa3abc /uv /bin/uv

COPY Makefile ./
COPY --from=builder /opt/app-root /opt/app-root

RUN uv sync --frozen --verbose
RUN make test
RUN touch ${IS_TESTED_FLAG}

#
# Production image
#
FROM base AS prod
COPY --from=builder /opt/app-root /opt/app-root
COPY --from=test ${IS_TESTED_FLAG} ${IS_TESTED_FLAG}

COPY app.sh ./
ENTRYPOINT [ "./app.sh" ]
