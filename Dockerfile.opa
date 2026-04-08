FROM registry.access.redhat.com/ubi9-minimal@sha256:d91be7cea9f03a757d69ad7fcdfcd7849dba820110e7980d5e2a1f46ed06ea3b AS base
COPY --from=openpolicyagent/opa:1.15.1-static@sha256:865ac441701302fc63844667df8e0acda7cf6ca796377eccf6c6177dcc3b7b24 /opa /opa

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
