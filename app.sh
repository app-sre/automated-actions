#!/bin/bash
echo "Starting Automated Actions ..."

if [[ "${AA_DEBUG}" == "1" ]]; then
    set -x
fi

if [ -r "settings.conf" ]; then
    set -a
    # shellcheck source=/dev/null
    . settings.conf
    set +a
fi

START_MODE="${AA_START_MODE:-api}"
APP_PORT="${AA_APP_PORT:-8080}"
UVICORN_OPTS="${AA_UVICORN_OPTS:- --host 0.0.0.0 --proxy-headers --forwarded-allow-ips=*}"
UVICORN_OPTS="${UVICORN_OPTS} --port ${APP_PORT}"
# start celery worker with solo pool by default to ensure only one worker is running
# we scale the number of workers using kubernetes pods
# this also ensures prometheus metrics are working
CELERY_OPTS="${AA_CELERY_OPTS:- --pool solo}"

if [[ "${AA_DEBUG}" == "1" ]]; then
    UVICORN_OPTS="${UVICORN_OPTS} --reload"
fi

if [[ "${START_MODE}" == "api" ]]; then
    echo "---> Serving application with uvicorn ..."
    # shellcheck disable=SC2086
    exec uvicorn $UVICORN_OPTS "$@" automated_actions.__main__:app
elif [[ "${START_MODE}" == "worker" ]]; then
    echo "---> Starting worker ..."
    # shellcheck disable=SC2086
    exec celery --app=automated_actions.worker worker ${CELERY_OPTS} "$@"
else
    echo "unknow mode $START_MODE - use 'api' or 'worker' instead"
fi
