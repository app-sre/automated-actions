FROM registry.access.redhat.com/ubi9-minimal@sha256:6fc28bcb6776e387d7a35a2056d9d2b985dc4e26031e98a2bd35a7137cd6fd71 AS base
COPY --from=openpolicyagent/opa:1.12.1-static@sha256:278deb6ffc725ca7e1939d56e9fded1f938c85a9a598def6d791598af57af61f /opa /opa

ENV PATH=${PATH}:/ \
    IS_TESTED_FLAG="/tmp/is_tested"

USER 1000:1000

COPY LICENSE /licenses/
COPY packages/opa/authz /authz

#
# Test image
#
FROM base AS test
COPY --from=ghcr.io/styrainc/regal:0.35.1@sha256:7caf9953f1c49054c94030ec7be087b46ae501fc347cdaace9557a57abd3f4ff /ko-app/regal /bin/regal

USER 0
RUN microdnf install -y make
USER 1000:1000

COPY packages/opa/Makefile /
COPY .regal.yaml /

RUN make -C / test
RUN touch ${IS_TESTED_FLAG}

#
# Prod image
#
FROM base AS prod
COPY --from=test ${IS_TESTED_FLAG} ${IS_TESTED_FLAG}

ENTRYPOINT ["/opa"]
CMD ["run"]
