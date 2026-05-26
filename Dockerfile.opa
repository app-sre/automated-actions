FROM registry.access.redhat.com/ubi10/ubi-minimal@sha256:5af8e51abe2a81b4247f05219284a627d37fb9ccf1055b90528a246fac11bc4d AS base
COPY --from=openpolicyagent/opa:1.16.2-static@sha256:bf5d926c9c5163cd43e56de43f47165d12c1e6a91911d0a20648f8e3ab085a61 /opa /opa

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
