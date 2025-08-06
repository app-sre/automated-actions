FROM registry.access.redhat.com/ubi9-minimal@sha256:e6b39b0a2cd88c0d904552eee0dca461bc74fe86fda3648ca4f8150913c79d0f AS base
COPY --from=openpolicyagent/opa:1.7.1-static@sha256:7ec12543a94d513f0381f4619386a380cdbdae48aed7929e84d68892650e6ce3 /opa /opa

ENV PATH=${PATH}:/
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

# Image does not have make installed, so we run the tests directly
RUN make -C / test

#
# Prod image
#
FROM base AS prod

ENTRYPOINT ["/opa"]
CMD ["run"]
